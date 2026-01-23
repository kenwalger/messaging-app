"""
Minimal backend HTTP & WebSocket server for Abiqua Asset Management.

References:
- API Contracts (#10)
- Functional Specification (#6)
- Architecture (#9)
- Resolved Specs & Clarifications

This module provides a minimal FastAPI server wrapper for local development.
All business logic remains in existing service modules.

TODO: Encryption and auth hardening
- Add TLS/HTTPS support for production
- Implement proper device authentication (currently header-based only)
- Add rate limiting and request validation
- Add request/response encryption
- Add proper error handling and logging
"""

import asyncio
import base64
import hashlib
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import UUID, uuid4

# Conditional import for cryptography (only needed in server encryption mode)
try:
    from cryptography.fernet import Fernet
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    Fernet = None  # type: ignore

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.backend.controller_api import ControllerAPIService
from src.backend.controller_auth import ControllerAuthService
from src.backend.conversation_api import ConversationService
from src.backend.conversation_registry import ConversationRegistry
from src.backend.device_registry import DeviceRegistry
from src.backend.identity_enforcement import IdentityEnforcementService
from src.backend.logging_service import LoggingService
from src.backend.message_relay import MessageRelayService
from src.backend.websocket_manager import FastAPIWebSocketManager
from src.shared.constants import (
    CLOCK_SKEW_TOLERANCE_MINUTES,
    DEFAULT_MESSAGE_EXPIRATION_DAYS,
    HEADER_CONTROLLER_KEY,
    HEADER_DEVICE_ID,
    MAX_MESSAGE_PAYLOAD_SIZE_KB,
)
from src.shared.controller_types import (
    ConfirmProvisioningRequest,
    ProvisionDeviceRequest,
    RevokeDeviceRequest,
)
from src.shared.device_identity_types import DeviceIdentityState
from src.shared.logging_types import LogEventType
from src.shared.message_types import utc_now

# Configure logging per Logging & Observability (#14)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager per FastAPI best practices.
    
    Replaces deprecated @app.on_event("startup") and @app.on_event("shutdown") decorators.
    Handles service initialization on startup and cleanup on shutdown.
    """
    global _device_registry, _conversation_registry, _identity_enforcement
    global _logging_service, _controller_auth, _controller_api
    global _conversation_service, _message_relay, _websocket_manager
    
    # Startup: Initialize services
    logger.info("Initializing Abiqua backend services...")
    
    # Initialize core services
    _device_registry = DeviceRegistry(demo_mode=DEMO_MODE)
    _conversation_registry = ConversationRegistry(_device_registry)
    _identity_enforcement = IdentityEnforcementService(_device_registry)
    _logging_service = LoggingService()
    _websocket_manager = FastAPIWebSocketManager()
    
    # Initialize controller services
    # TODO: Replace with proper configuration management
    # Load controller API keys from environment variable
    controller_api_keys = os.getenv("CONTROLLER_API_KEYS", "test-controller-key").split(",")
    # Remove empty strings and strip whitespace
    controller_api_keys = [key.strip() for key in controller_api_keys if key.strip()]
    # Fallback to test key for development if no keys provided
    if not controller_api_keys:
        logger.warning("No CONTROLLER_API_KEYS environment variable set, using test key for development")
        controller_api_keys = ["test-controller-key"]
    
    _controller_auth = ControllerAuthService(valid_api_keys=controller_api_keys)
    _controller_api = ControllerAPIService(
        device_registry=_device_registry,
        conversation_registry=_conversation_registry,
        identity_enforcement=_identity_enforcement,
        logging_service=_logging_service,
        controller_auth=_controller_auth,
    )
    
    # Initialize conversation service
    _conversation_service = ConversationService(
        conversation_registry=_conversation_registry,
        device_registry=_device_registry,
        log_service=_logging_service,
    )
    
    # Initialize message relay service
    _message_relay = MessageRelayService(
        device_registry=_device_registry,
        websocket_manager=_websocket_manager,
        log_service=_logging_service,
    )
    
    # Start WebSocket background task for message delivery
    event_loop = asyncio.get_event_loop()
    _websocket_manager.start_background_task(event_loop)
    
    logger.info("Abiqua backend services initialized")
    
    # Yield control to application
    yield
    
    # Shutdown: Clean up services
    if _websocket_manager:
        _websocket_manager.stop_background_task()
        logger.info("Abiqua backend services shut down")


# Create FastAPI application with lifespan context manager
app = FastAPI(
    title="Abiqua Asset Management API",
    description="Secure messaging system for high-risk environments",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS for local development
# Only enable permissive CORS in development (when running locally)
# Production should use strict CORS configuration
is_development = os.getenv("ENVIRONMENT", "development").lower() in ("development", "dev", "local")

# Encryption mode configuration
# "server": Accept plaintext payloads, encrypt server-side (dev/POC mode only)
# "client": Require hex/base64 encoded encrypted payloads (production mode)
ENCRYPTION_MODE = os.getenv("ENCRYPTION_MODE", "client").lower()
if ENCRYPTION_MODE not in ("server", "client"):
    logger.warning(f"Invalid ENCRYPTION_MODE '{ENCRYPTION_MODE}', defaulting to 'client'")
    ENCRYPTION_MODE = "client"

# Demo mode configuration
# When enabled, allows HTTP-first messaging with lenient device validation
# WebSockets become best-effort delivery, not authorization requirement
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes", "on")
if DEMO_MODE:
    logger.info("🧪 DEMO MODE ENABLED - WebSocket optional, encryption enforced, lenient device validation")

# Server-side encryption key (dev/POC mode only)
# In production, encryption should be client-side only
# This key is derived from a fixed seed for dev mode consistency
if ENCRYPTION_MODE == "server":
    if not CRYPTOGRAPHY_AVAILABLE:
        logger.error("ENCRYPTION_MODE=server requires cryptography package. Install with: pip install cryptography")
        raise ImportError("cryptography package required for server-side encryption mode")
    # Generate a deterministic key for dev mode (not secure for production)
    key_seed = os.getenv("ENCRYPTION_KEY_SEED", "dev-mode-encryption-key-seed")
    key_bytes = hashlib.sha256(key_seed.encode()).digest()
    _server_encryption_key = base64.urlsafe_b64encode(key_bytes)
    _server_encryptor = Fernet(_server_encryption_key)
    logger.info(f"Server-side encryption enabled (dev/POC mode) - ENCRYPTION_MODE={ENCRYPTION_MODE}")
else:
    _server_encryptor = None
    logger.info(f"Client-side encryption required (production mode) - ENCRYPTION_MODE={ENCRYPTION_MODE}")

# CORS configuration
# Allow frontend origin from environment variable (for Heroku deployment)
# Or use development origins for local development
frontend_origin = os.getenv("FRONTEND_ORIGIN")
if is_development:
    # Permissive CORS for local development
    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    if frontend_origin:
        allowed_origins.append(frontend_origin)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-Device-ID",
            "X-Controller-Key",
        ],
        expose_headers=[],
        max_age=3600,
    )
    logger.info(f"CORS enabled for local development: {allowed_origins}")
elif frontend_origin:
    # Production with frontend origin specified (Heroku deployment)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[frontend_origin],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-Device-ID",
            "X-Controller-Key",
        ],
        expose_headers=[],
        max_age=3600,
    )
    logger.info(f"CORS enabled for production frontend: {frontend_origin}")
else:
    # Production: Strict CORS (no middleware added - will reject cross-origin requests)
    logger.info("CORS disabled - production mode (strict security, no FRONTEND_ORIGIN set)")

# Global service instances (initialized in startup)
# TODO: Replace with proper dependency injection container
_device_registry: Optional[DeviceRegistry] = None
_conversation_registry: Optional[ConversationRegistry] = None
_identity_enforcement: Optional[IdentityEnforcementService] = None
_logging_service: Optional[LoggingService] = None
_controller_auth: Optional[ControllerAuthService] = None
_controller_api: Optional[ControllerAPIService] = None
_conversation_service: Optional[ConversationService] = None
_message_relay: Optional[MessageRelayService] = None
_websocket_manager: Optional[FastAPIWebSocketManager] = None


def get_device_registry() -> DeviceRegistry:
    """Get device registry instance."""
    if _device_registry is None:
        raise RuntimeError("Device registry not initialized")
    return _device_registry


def get_conversation_registry() -> ConversationRegistry:
    """Get conversation registry instance."""
    if _conversation_registry is None:
        raise RuntimeError("Conversation registry not initialized")
    return _conversation_registry


def get_logging_service() -> LoggingService:
    """Get logging service instance."""
    if _logging_service is None:
        raise RuntimeError("Logging service not initialized")
    return _logging_service


def get_controller_auth() -> ControllerAuthService:
    """Get controller auth service instance."""
    if _controller_auth is None:
        raise RuntimeError("Controller auth service not initialized")
    return _controller_auth


def get_controller_api() -> ControllerAPIService:
    """Get controller API service instance."""
    if _controller_api is None:
        raise RuntimeError("Controller API service not initialized")
    return _controller_api


def get_conversation_service() -> ConversationService:
    """Get conversation service instance."""
    if _conversation_service is None:
        raise RuntimeError("Conversation service not initialized")
    return _conversation_service


def get_message_relay() -> MessageRelayService:
    """Get message relay service instance."""
    if _message_relay is None:
        raise RuntimeError("Message relay service not initialized")
    return _message_relay


def get_websocket_manager() -> FastAPIWebSocketManager:
    """Get WebSocket manager instance."""
    if _websocket_manager is None:
        raise RuntimeError("WebSocket manager not initialized")
    return _websocket_manager


def get_device_id(device_id: Optional[str] = Header(None, alias=HEADER_DEVICE_ID)) -> str:
    """
    Extract device ID from X-Device-ID header per API Contracts (#10), Section 5.
    
    Args:
        device_id: Device ID from X-Device-ID header.
    
    Returns:
        Device ID string.
    
    Raises:
        HTTPException: If device ID is missing.
    """
    if not device_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device ID required in X-Device-ID header",
        )
    return device_id


def create_error_response(
    reason_code: str,
    message: str,
    request_id: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
) -> JSONResponse:
    """
    Create structured error response with error_code, message, and request_id.
    
    Args:
        reason_code: Machine-readable error code.
        message: Human-readable error message.
        request_id: Request identifier for correlation.
        status_code: HTTP status code (defaults to 400).
    
    Returns:
        JSONResponse with error structure.
    """
    return JSONResponse(
        content={
            "error_code": reason_code,
            "message": message,
            "request_id": request_id,
        },
        status_code=status_code,
    )




# ============================================================================
# Controller API Endpoints
# ============================================================================

@app.post("/api/device/provision")
async def provision_device(
    request: ProvisionDeviceRequest,
    controller_key: Optional[str] = Header(None, alias=HEADER_CONTROLLER_KEY),
) -> JSONResponse:
    """
    Provision device endpoint per API Contracts (#10), Section 3.1.
    
    Creates device in Pending state per Identity Provisioning (#11), Section 3.
    """
    controller_api = get_controller_api()
    result = controller_api.provision_device(request, controller_key)
    return JSONResponse(
        content=result["response"],
        status_code=result["status_code"],
    )


@app.post("/api/device/provision/confirm")
async def confirm_provisioning(
    request: ConfirmProvisioningRequest,
    controller_key: Optional[str] = Header(None, alias=HEADER_CONTROLLER_KEY),
) -> JSONResponse:
    """
    Confirm device provisioning endpoint per Identity Provisioning (#11), Section 3.
    
    Transitions Pending → Provisioned per State Machines (#7), Section 5.
    """
    controller_api = get_controller_api()
    result = controller_api.confirm_provisioning(request, controller_key)
    return JSONResponse(
        content=result["response"],
        status_code=result["status_code"],
    )


@app.post("/api/device/revoke")
async def revoke_device(
    request: RevokeDeviceRequest,
    controller_key: Optional[str] = Header(None, alias=HEADER_CONTROLLER_KEY),
) -> JSONResponse:
    """
    Revoke device endpoint per API Contracts (#10), Section 3.2.
    
    Revocation is immediate and irreversible per Identity Provisioning (#11), Section 5.
    """
    controller_api = get_controller_api()
    result = controller_api.revoke_device(request, controller_key)
    return JSONResponse(
        content=result["response"],
        status_code=result["status_code"],
    )


# ============================================================================
# Conversation API Endpoints
# ============================================================================

class CreateConversationRequest(BaseModel):
    """
    Request model for creating a conversation.
    
    Per API Contracts (#10) and Functional Spec (#6), Section 4.1.
    """
    participants: List[str] = Field(..., min_length=1, description="List of participant device IDs")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "participants": ["device-001", "device-002"]
            }
        }
    }


@app.post("/api/conversation/create")
async def create_conversation(
    request: CreateConversationRequest,
    device_id: str = Depends(get_device_id),
) -> JSONResponse:
    """
    Create conversation endpoint per API Contracts (#10) and Functional Spec (#6), Section 4.1.
    
    Request body: { "participants": ["device-001", "device-002"] }
    Response: { "conversation_id": "<uuid>", "participants": ["device-001", "device-002"], "status": "success" }
    
    The calling device (from X-Device-ID header) is automatically included in participants if not present.
    Empty participant lists are rejected with 400 Bad Request.
    """
    # Generate request_id for this request
    request_id = str(uuid4())
    
    # Get services
    conversation_service = get_conversation_service()
    logging_service = get_logging_service()
    
    # Extract participants from request
    participants = request.participants
    
    # Validation: Reject empty participant lists with clear 400 error
    if not participants:
        reason_code = "participants_required"
        if logging_service:
            logging_service.log_event(
                "conversation_creation_failed",
                {
                    "request_id": request_id,
                    "device_id": device_id,
                    "reason_code": reason_code,
                },
            )
        return JSONResponse(
            content={
                "error_code": reason_code,
                "message": "Invalid request: participants list cannot be empty",
                "request_id": request_id,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    # Ensure calling device is included in participants
    if device_id not in participants:
        participants = [device_id] + participants
    
    # Call conversation service
    result = conversation_service.create_conversation(device_id, participants)
    
    # Return structured response
    status_code = result.get("status_code", 200)
    if status_code == 200:
        # Success response with required fields
        response_content = {
            "conversation_id": result.get("conversation_id"),
            "participants": result.get("participants", participants),
            "status": "success",
        }
    else:
        # Error response with structured format
        response_content = {
            "error_code": result.get("error_code", "conversation_creation_failed"),
            "message": result.get("message", "Failed to create conversation"),
            "request_id": request_id,
        }
    
    return JSONResponse(content=response_content, status_code=status_code)


@app.post("/api/conversation/join")
async def join_conversation(
    conversation_id: str,
    device_id: str = Depends(get_device_id),
) -> JSONResponse:
    """
    Join conversation endpoint per API Contracts (#10) and State Machines (#7), Section 4.
    """
    conversation_service = get_conversation_service()
    result = conversation_service.join_conversation(device_id, conversation_id)
    
    status_code = result.get("status_code", 200)
    return JSONResponse(content=result, status_code=status_code)


@app.post("/api/conversation/leave")
async def leave_conversation(
    conversation_id: str,
    device_id: str = Depends(get_device_id),
) -> JSONResponse:
    """
    Leave conversation endpoint per API Contracts (#10) and State Machines (#7), Section 4.
    """
    conversation_service = get_conversation_service()
    result = conversation_service.leave_conversation(device_id, conversation_id)
    
    status_code = result.get("status_code", 200)
    return JSONResponse(content=result, status_code=status_code)


@app.post("/api/conversation/close")
async def close_conversation(
    conversation_id: str,
    device_id: str = Depends(get_device_id),
) -> JSONResponse:
    """
    Close conversation endpoint per API Contracts (#10) and State Machines (#7), Section 4.
    """
    conversation_service = get_conversation_service()
    result = conversation_service.close_conversation(device_id, conversation_id)
    
    status_code = result.get("status_code", 200)
    return JSONResponse(content=result, status_code=status_code)


@app.get("/api/conversation/info")
async def get_conversation_info(
    conversation_id: str,
    device_id: str = Depends(get_device_id),
) -> JSONResponse:
    """
    Get conversation info endpoint per API Contracts (#10).
    """
    conversation_service = get_conversation_service()
    result = conversation_service.get_conversation_info(device_id, conversation_id)
    
    status_code = result.get("status_code", 200)
    return JSONResponse(content=result, status_code=status_code)


# ============================================================================
# Message API Endpoints
# ============================================================================

@app.post("/api/message/send")
async def send_message(
    request: Dict[str, Any],
    device_id: str = Depends(get_device_id),
) -> JSONResponse:
    """
    Send message endpoint per API Contracts (#10), Section 3.3.
    
    Sends encrypted message; backend stores payload temporarily for delivery.
    Message enters PendingDelivery state and is forwarded to recipients via WebSocket or offline queue.
    
    Request body: { conversation_id: string, payload: string, expiration?: ISO timestamp }
    Response: { message_id: string, timestamp: ISO timestamp, status: "queued" }
    
    Payload Encoding Requirements:
    - ENCRYPTION_MODE=client (default/production): Payload must be hex or base64 encoded encrypted bytes
    - ENCRYPTION_MODE=server (dev/POC only): Payload can be plaintext; server encrypts before persistence/delivery
    
    Validation checks that can return 400 Bad Request:
    1. conversation_id_required: conversation_id field is missing or empty
    2. payload_required: payload field is missing or empty
    3. payload_not_string: payload is not a string type
    4. payload_encoding_invalid: payload cannot be decoded as base64 or hex (client mode only)
    5. payload_plaintext_rejected: plaintext payload sent when client-side encryption required
    6. payload_size_exceeded: payload size exceeds MAX_MESSAGE_PAYLOAD_SIZE_KB (50KB)
    7. conversation_not_active: conversation exists but is not in ACTIVE state
    8. no_recipients_available: conversation has only the sender (no other participants)
    9. expiration_invalid_format: expiration timestamp is not valid ISO 8601 format
    10. expiration_not_future: expiration timestamp is not in the future
    """
    # Generate request_id for this request
    request_id = str(uuid4())
    
    # Get services
    device_registry = get_device_registry()
    logging_service = get_logging_service()
    
    # Demo mode: Mark device as seen early (for activity TTL tracking)
    # This must be called before validation to refresh activity TTL for HTTP-first messaging
    if DEMO_MODE:
        device_registry.mark_device_seen(device_id)
        logger.debug(f"[DEMO MODE] Device {device_id} marked as seen (activity TTL refreshed early)")
    
    # Validate device exists and is ACTIVE
    # Development mode: Auto-provision devices for local development convenience
    if is_development and not device_registry.is_device_active(device_id):
        existing_device = device_registry.get_device_identity(device_id)
        if existing_device is None:
            # Device doesn't exist - auto-register, provision, and confirm for development
            try:
                device_registry.register_device(
                    device_id=device_id,
                    public_key="dev-auto-provisioned-key",  # Placeholder for development
                    controller_id="dev-auto-provision",
                )
                device_registry.provision_device(device_id)
                device_registry.confirm_provisioning(device_id)
                logger.info(f"Auto-provisioned device {device_id} for development")
            except ValueError:
                # Device might have been registered by another request
                if not device_registry.is_device_active(device_id):
                    reason_code = "device_not_active"
                    if logging_service:
                        logger.warning(
                            f"Message send rejected: {reason_code}",
                            extra={
                                "request_id": request_id,
                                "device_id": device_id,
                                "reason_code": reason_code,
                            },
                        )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Device not active",
                    )
        else:
            # Device exists but not active - try to complete provisioning
            try:
                if existing_device.state == DeviceIdentityState.PENDING:
                    device_registry.provision_device(device_id)
                    device_registry.confirm_provisioning(device_id)
                elif existing_device.state == DeviceIdentityState.PROVISIONED:
                    device_registry.confirm_provisioning(device_id)
            except Exception:
                pass  # If provisioning fails, continue to check active status
    
    # Final check: device must be active (unless in demo mode)
    if not DEMO_MODE and not device_registry.is_device_active(device_id):
        reason_code = "device_not_active"
        if logging_service:
            logger.warning(
                f"Message send rejected: {reason_code}",
                extra={
                    "request_id": request_id,
                    "device_id": device_id,
                    "reason_code": reason_code,
                },
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device not active",
        )
    elif DEMO_MODE and not device_registry.is_device_active(device_id):
        # In demo mode, log warning but allow message send (activity TTL will handle it)
        logger.warning(f"[DEMO MODE] Device {device_id} not in Active state, but allowing message send (activity TTL)")
    
    # Extract required request fields per API Contracts (#10), Section 3.3
    conversation_id = request.get("conversation_id", "")
    payload = request.get("payload", "")  # Encrypted payload (base64 or hex string)
    expiration = request.get("expiration")  # ISO timestamp string (optional)
    
    # Validation check 1: conversation_id_required
    if not conversation_id:
        reason_code = "conversation_id_required"
        if logging_service:
            logger.warning(
                f"Message send rejected: {reason_code}",
                extra={
                    "request_id": request_id,
                    "device_id": device_id,
                    "reason_code": reason_code,
                },
            )
        return create_error_response(
            reason_code=reason_code,
            message="Invalid request: conversation_id is required",
            request_id=request_id,
        )
    
    # Validation check 2: payload_required
    if not payload:
        reason_code = "payload_required"
        if logging_service:
            logger.warning(
                f"Message send rejected: {reason_code}",
                extra={
                    "request_id": request_id,
                    "device_id": device_id,
                    "conversation_id": conversation_id,
                    "reason_code": reason_code,
                },
            )
        return create_error_response(
            reason_code=reason_code,
            message="Invalid request: payload is required",
            request_id=request_id,
        )
    
    # Validation check 3: payload_not_string
    if not isinstance(payload, str):
        reason_code = "payload_not_string"
        if logging_service:
            logger.warning(
                f"Message send rejected: {reason_code}",
                extra={
                    "request_id": request_id,
                    "device_id": device_id,
                    "conversation_id": conversation_id,
                    "reason_code": reason_code,
                },
            )
        return create_error_response(
            reason_code=reason_code,
            message="Invalid request: payload must be a string",
            request_id=request_id,
        )
    
    # Assign message_id server-side per API Contracts (#10), Section 3.3
    message_id = uuid4()
    
    # Use server timestamp per API Contracts (#10), Section 3.3
    message_timestamp = utc_now()
    
    # Process payload based on encryption mode
    if ENCRYPTION_MODE == "server":
        # Server-side encryption mode (dev/POC only): accept plaintext, encrypt server-side
        # Try to decode as encrypted payload first (in case client sent encrypted)
        encrypted_payload = None
        try:
            import binascii
            encrypted_payload = base64.b64decode(payload, validate=True)
        except (binascii.Error, ValueError, TypeError):
            try:
                encrypted_payload = bytes.fromhex(payload)
            except (ValueError, TypeError):
                # Not base64 or hex - assume plaintext and encrypt server-side
                try:
                    plaintext_payload = payload.encode("utf-8")
                    encrypted_payload = _server_encryptor.encrypt(plaintext_payload)
                except Exception as e:
                    reason_code = "payload_encoding_invalid"
                    if logging_service:
                        logger.warning(
                            f"Message send rejected: {reason_code}",
                            extra={
                                "request_id": request_id,
                                "device_id": device_id,
                                "conversation_id": conversation_id,
                                "reason_code": reason_code,
                            },
                        )
                    return create_error_response(
                        reason_code=reason_code,
                        message=f"Invalid payload: {e}",
                        request_id=request_id,
                    )
    else:
        # Client-side encryption mode (production): require hex or base64 encoded encrypted payload
        # Validation check 4: payload_encoding_invalid
        encrypted_payload = None
        # Try base64 decoding with validation
        try:
            import binascii
            # Use validate=True to ensure payload is actually valid base64
            encrypted_payload = base64.b64decode(payload, validate=True)
        except (binascii.Error, ValueError, TypeError):
            # Not valid base64 - try hex decoding as fallback
            try:
                encrypted_payload = bytes.fromhex(payload)
            except (ValueError, TypeError) as e:
                # Check if payload looks like plaintext (contains printable ASCII characters)
                # This is a heuristic - if it's valid UTF-8 and mostly printable, it's likely plaintext
                is_plaintext = False
                try:
                    payload_bytes = payload.encode("utf-8")
                    if len(payload_bytes) > 0:
                        # Check if payload is mostly printable ASCII (heuristic for plaintext detection)
                        # Count printable bytes (32-126 are printable ASCII, 9/10/13 are tab/newline/carriage return)
                        printable_count = sum(1 for b in payload_bytes if 32 <= b <= 126 or b in (9, 10, 13))
                        # If 80% or more of bytes are printable, consider it plaintext
                        if printable_count >= len(payload_bytes) * 0.8:
                            is_plaintext = True
                except Exception:
                    pass  # Not UTF-8, not plaintext
                
                if is_plaintext:
                    # Validation check 5: payload_plaintext_rejected
                    reason_code = "payload_plaintext_rejected"
                    if logging_service:
                        logger.warning(
                            f"Message send rejected: {reason_code}",
                            extra={
                                "request_id": request_id,
                                "device_id": device_id,
                                "conversation_id": conversation_id,
                                "reason_code": reason_code,
                            },
                        )
                    return create_error_response(
                        reason_code=reason_code,
                        message="Invalid request: payload must be encrypted (hex or base64 encoded). Plaintext is not accepted in client-side encryption mode.",
                        request_id=request_id,
                    )
                
                reason_code = "payload_encoding_invalid"
                if logging_service:
                    logger.warning(
                        f"Message send rejected: {reason_code}",
                        extra={
                            "request_id": request_id,
                            "device_id": device_id,
                            "conversation_id": conversation_id,
                            "reason_code": reason_code,
                        },
                    )
                return create_error_response(
                    reason_code=reason_code,
                    message=f"Invalid payload encoding: {e}",
                    request_id=request_id,
                )
    
    # Validation check 6: payload_size_exceeded
    payload_size_kb = len(encrypted_payload) / 1024
    if payload_size_kb > MAX_MESSAGE_PAYLOAD_SIZE_KB:
        reason_code = "payload_size_exceeded"
        if logging_service:
            logger.warning(
                f"Message send rejected: {reason_code}",
                extra={
                    "request_id": request_id,
                    "device_id": device_id,
                    "conversation_id": conversation_id,
                    "reason_code": reason_code,
                    "payload_size_kb": payload_size_kb,
                    "max_size_kb": MAX_MESSAGE_PAYLOAD_SIZE_KB,
                },
            )
        return create_error_response(
            reason_code=reason_code,
            message=f"Invalid request: payload size ({payload_size_kb:.1f}KB) exceeds maximum ({MAX_MESSAGE_PAYLOAD_SIZE_KB}KB)",
            request_id=request_id,
        )
    
    # Validate conversation exists and is ACTIVE
    conversation_registry = get_conversation_registry()
    
    # Get conversation participants and check conversation state
    participants = conversation_registry.get_conversation_participants(conversation_id)
    
    # Check if conversation exists (regardless of state)
    conversation_exists = conversation_registry.conversation_exists(conversation_id)
    
    # Check if conversation is ACTIVE
    is_active = conversation_registry.is_conversation_active(conversation_id)
    
    # If conversation doesn't exist, return 404
    # Note: 404 errors don't use structured format (per API Contracts)
    if not conversation_exists:
        reason_code = "conversation_not_found"
        if logging_service:
            logger.warning(
                f"Message send rejected: {reason_code}",
                extra={
                    "request_id": request_id,
                    "device_id": device_id,
                    "conversation_id": conversation_id,
                    "reason_code": reason_code,
                },
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    
    # If conversation exists but is not active, return 400
    # Validation check 7: conversation_not_active
    if not is_active:
        reason_code = "conversation_not_active"
        if logging_service:
            logger.warning(
                f"Message send rejected: {reason_code}",
                extra={
                    "request_id": request_id,
                    "device_id": device_id,
                    "conversation_id": conversation_id,
                    "reason_code": reason_code,
                },
            )
        return create_error_response(
            reason_code=reason_code,
            message="Invalid request: conversation is not active",
            request_id=request_id,
        )
    
    # Authorization check: Verify sender is a participant in the conversation
    if device_id not in participants:
        reason_code = "sender_not_participant"
        if logging_service:
            logger.warning(
                f"Message send rejected: {reason_code}",
                extra={
                    "request_id": request_id,
                    "device_id": device_id,
                    "conversation_id": conversation_id,
                    "reason_code": reason_code,
                },
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid request: sender is not a participant in this conversation",
        )
    
    # Exclude sender from recipients (they shouldn't receive their own message)
    recipients = [p for p in participants if p != device_id]
    
    # Validation check 8: no_recipients_available
    if not recipients:
        reason_code = "no_recipients_available"
        if logging_service:
            logger.warning(
                f"Message send rejected: {reason_code}",
                extra={
                    "request_id": request_id,
                    "device_id": device_id,
                    "conversation_id": conversation_id,
                    "reason_code": reason_code,
                },
            )
        return create_error_response(
            reason_code=reason_code,
            message="Invalid request: no recipients available (conversation has only sender)",
            request_id=request_id,
        )
    
    # Parse expiration timestamp (use provided or derive from server timestamp + default expiration)
    if expiration:
        try:
            expiration_timestamp = datetime.fromisoformat(expiration.replace("Z", "+00:00"))
            # Validation check 10: expiration_not_future
            if expiration_timestamp <= message_timestamp:
                reason_code = "expiration_not_future"
                if logging_service:
                    logger.warning(
                        f"Message send rejected: {reason_code}",
                        extra={
                            "request_id": request_id,
                            "device_id": device_id,
                            "conversation_id": conversation_id,
                            "reason_code": reason_code,
                        },
                    )
                return create_error_response(
                    reason_code=reason_code,
                    message="Invalid request: expiration must be in the future",
                    request_id=request_id,
                )
        except (ValueError, AttributeError) as e:
            # Validation check 9: expiration_invalid_format
            reason_code = "expiration_invalid_format"
            if logging_service:
                logger.warning(
                    f"Message send rejected: {reason_code}",
                    extra={
                        "request_id": request_id,
                        "device_id": device_id,
                        "conversation_id": conversation_id,
                        "reason_code": reason_code,
                    },
                )
            return create_error_response(
                reason_code=reason_code,
                message=f"Invalid expiration timestamp: {e}",
                request_id=request_id,
            )
    else:
        # Derive expiration from server timestamp + default expiration days
        expiration_timestamp = message_timestamp + timedelta(days=DEFAULT_MESSAGE_EXPIRATION_DAYS)
    
    # Log message send attempt (metadata only, no content) per Logging & Observability (#14)
    if logging_service:
        logging_service.log_event(
            LogEventType.MESSAGE_ATTEMPTED,
            {
                "message_id": str(message_id),
                "conversation_id": conversation_id,
                "sender_id": device_id,
                "recipient_count": len(recipients),
                "message_size_bytes": len(encrypted_payload),
                "timestamp": message_timestamp.isoformat(),
            },
        )
    
    # Demo mode: Mark device as seen again after successful validation
    # This ensures activity TTL is refreshed on every HTTP message send
    if DEMO_MODE:
        device_registry.mark_device_seen(device_id)
        logger.debug(f"[DEMO MODE] Device {device_id} activity TTL refreshed after message validation")
    
    # Relay message via MessageRelayService (enters PendingDelivery state)
    message_relay = get_message_relay()
    success = message_relay.relay_message(
        sender_id=device_id,
        recipients=recipients,
        encrypted_payload=encrypted_payload,
        message_id=message_id,
        expiration_timestamp=expiration_timestamp,
        conversation_id=conversation_id,
    )
    
    if not success:
        # Log delivery failure (metadata only)
        if logging_service:
            logging_service.log_event(
                LogEventType.DELIVERY_FAILED,
                {
                    "message_id": str(message_id),
                    "conversation_id": conversation_id,
                    "sender_id": device_id,
                },
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Backend failure",
        )
    
    # Return response per API Contracts (#10), Section 3.3
    # Response format: { message_id, timestamp, status }
    response_content = {
        "message_id": str(message_id),
        "timestamp": message_timestamp.isoformat(),
        "status": "queued",
    }
    
    # In demo mode, add warning about WebSocket being optional
    if DEMO_MODE:
        response_content["demo_mode_warning"] = "WebSocket delivery is best-effort; message queued for REST polling"
        logger.debug(f"[DEMO MODE] Message {message_id} accepted (WebSocket optional)")
    
    return JSONResponse(
        content=response_content,
        status_code=status.HTTP_202_ACCEPTED,
    )


@app.get("/api/message/receive")
async def receive_message(
    device_id: str = Depends(get_device_id),
    last_received_id: Optional[str] = None,
) -> JSONResponse:
    """
    Receive message endpoint per API Contracts (#10), Section 3.4.
    
    Returns encrypted messages delivered to this device.
    """
    message_relay = get_message_relay()
    
    # Parse last_received_id if provided
    last_received_uuid = None
    if last_received_id:
        try:
            last_received_uuid = UUID(last_received_id)
        except ValueError:
            # Invalid UUID format, ignore pagination
            pass
    
    messages = message_relay.get_pending_messages(device_id, last_received_uuid)
    
    # Messages are already formatted by MessageRelayService.get_pending_messages()
    # They contain hex-encoded payloads per API Contracts (#10), Section 3.4
    formatted_messages = messages
    
    return JSONResponse(
        content={
            "messages": formatted_messages,
            "api_version": "v1",
            "timestamp": utc_now().isoformat(),
        },
        status_code=status.HTTP_200_OK,
    )


# ============================================================================
# Logging API Endpoints
# ============================================================================

@app.post("/api/log/event")
async def log_event(
    request: Dict[str, Any],
    device_id: str = Depends(get_device_id),
) -> JSONResponse:
    """
    Log operational event endpoint per API Contracts (#10), Section 3.5.
    
    Records content-free operational events only.
    """
    event_type = request.get("event_type")
    timestamp = request.get("timestamp")
    
    if not event_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request: event_type required",
        )
    
    logging_service = get_logging_service()
    
    # Parse timestamp if provided
    event_timestamp = None
    if timestamp:
        try:
            event_timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except Exception:
            event_timestamp = None
    
    # Log event (content-free validation enforced by LoggingService)
    try:
        log_event_type = LogEventType(event_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid event_type: {event_type}",
        )
    
    # Include device_id in event_data per Logging & Observability (#14)
    event_data = request.get("event_data", {})
    event_data["device_id"] = device_id
    
    logging_service.log_event(
        event_type=log_event_type,
        event_data=event_data,
    )
    
    return JSONResponse(
        content={
            "status": "logged",
            "api_version": "v1",
            "timestamp": utc_now().isoformat(),
        },
        status_code=status.HTTP_200_OK,
    )


# ============================================================================
# Development Bootstrap Endpoint
# ============================================================================

@app.post("/api/dev/bootstrap")
async def bootstrap_dev_data() -> JSONResponse:
    """
    Development-only endpoint to bootstrap test data.
    
    Creates:
    - One active device (device-001)
    - One active conversation (conv-001) with device-001 as participant
    
    This endpoint is only available in development mode.
    Does NOT modify production behavior.
    """
    # Only available in development mode
    if not is_development:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )
    
    device_registry = get_device_registry()
    conversation_registry = get_conversation_registry()
    
    # Create active device if it doesn't exist
    device_id = "device-001"
    if not device_registry.is_device_active(device_id):
        # Register, provision, and confirm device
        device_registry.register_device(device_id, "dev-public-key", "dev-controller")
        device_registry.provision_device(device_id)
        device_registry.confirm_provisioning(device_id)
    
    # Create active conversation if it doesn't exist
    conversation_id = "conv-001"
    if not conversation_registry.conversation_exists(conversation_id):
        conversation_registry.register_conversation(conversation_id, [device_id])
    
    return JSONResponse(
        content={
            "status": "bootstrap_complete",
            "device_id": device_id,
            "conversation_id": conversation_id,
            "message": "Development data created successfully",
        },
        status_code=status.HTTP_200_OK,
    )


# ============================================================================
# WebSocket Endpoint
# ============================================================================

@app.websocket("/ws/messages")
async def websocket_messages(
    websocket: WebSocket,
    device_id: Optional[str] = None,
) -> None:
    """
    WebSocket endpoint for message delivery per API Contracts (#10).
    
    Devices connect via WebSocket for real-time message delivery.
    Device ID should be provided as query parameter or header.
    """
    # Extract device_id from query parameters or headers
    if not device_id:
        # Try to get from query params
        device_id = websocket.query_params.get("device_id")
    
    if not device_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Validate device is active
    device_registry = get_device_registry()
    
    # Demo mode: Mark device as seen and auto-register if needed
    if DEMO_MODE:
        device_registry.mark_device_seen(device_id)
        existing_device = device_registry.get_device_identity(device_id)
        if existing_device is None:
            # Auto-register device in demo mode
            try:
                device_registry.register_device(device_id, "demo-public-key", "demo-controller")
                device_registry.provision_device(device_id)
                device_registry.confirm_provisioning(device_id)
                logger.info(f"[DEMO MODE] Auto-registered device {device_id} for WebSocket connection")
            except Exception as e:
                logger.warning(f"[DEMO MODE] Failed to auto-register device {device_id}: {e}")
        # In demo mode, allow WebSocket connection even if device not strictly active
        if not device_registry.is_device_active(device_id):
            logger.warning(f"[DEMO MODE] Device {device_id} not strictly active, but allowing WebSocket connection (activity TTL)")
    # Development mode: Auto-provision devices for local development convenience
    # In production, devices must be provisioned via Controller API first
    elif is_development and not device_registry.is_device_active(device_id):
        existing_device = device_registry.get_device_identity(device_id)
        if existing_device is None:
            # Device doesn't exist - auto-register, provision, and confirm for development
            try:
                # Register device in Pending state
                device_registry.register_device(
                    device_id=device_id,
                    public_key="dev-auto-provisioned-key",  # Placeholder for development
                    controller_id="dev-auto-provision",
                )
                # Provision device (Pending → Provisioned)
                device_registry.provision_device(device_id)
                # Confirm provisioning (Provisioned → Active)
                device_registry.confirm_provisioning(device_id)
                logger.info(f"Auto-provisioned device {device_id} for local development")
            except ValueError as e:
                # Device might have been registered between check and register
                # Or provisioning failed - log and continue to check if now active
                logger.debug(f"Auto-provisioning attempt for {device_id}: {e}")
        else:
            # Device exists but not active - try to complete provisioning
            from src.shared.device_identity_types import DeviceIdentityState
            try:
                if existing_device.state == DeviceIdentityState.PENDING:
                    # Provision device (Pending → Provisioned)
                    device_registry.provision_device(device_id)
                    # Confirm provisioning (Provisioned → Active)
                    device_registry.confirm_provisioning(device_id)
                    logger.info(f"Auto-completed provisioning for device {device_id} (was Pending)")
                elif existing_device.state == DeviceIdentityState.PROVISIONED:
                    # Confirm provisioning (Provisioned → Active)
                    device_registry.confirm_provisioning(device_id)
                    logger.info(f"Auto-confirmed provisioning for device {device_id} (was Provisioned)")
            except ValueError as e:
                # State transition validation failed - log and continue to check if now active
                logger.debug(f"Auto-provisioning completion attempt for {device_id}: {e}")
        
        # Check again if device is now active (might have been provisioned by another request)
        if not device_registry.is_device_active(device_id):
            # Still not active - close connection (unless in demo mode)
            if not DEMO_MODE:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
            else:
                logger.warning(f"[DEMO MODE] Device {device_id} not strictly active, but allowing WebSocket connection")
    elif not DEMO_MODE and not device_registry.is_device_active(device_id):
        # Production mode: Device must be provisioned via Controller API
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Connect WebSocket
    websocket_manager = get_websocket_manager()
    await websocket_manager.connect(device_id, websocket)
    
    try:
        # Keep connection alive and handle incoming messages
        while True:
            # Wait for messages (ACKs, etc.)
            data = await websocket.receive_text()
            
            # Parse incoming message (e.g., delivery ACK)
            try:
                message = json.loads(data)
                
                # Handle delivery ACK per API Contracts (#10)
                if message.get("type") == "ack" and message.get("message_id"):
                    message_id_str = message.get("message_id")
                    conversation_id = message.get("conversation_id", "")
                    
                    try:
                        from uuid import UUID
                        message_id = UUID(message_id_str)
                    except ValueError:
                        logger.warning(f"Invalid message_id in ACK from {device_id}: {message_id_str}")
                        continue
                    
                    # Get sender_id and conversation_id before acknowledging
                    # (metadata may be deleted after ACK if all recipients delivered)
                    message_relay = get_message_relay()
                    sender_id = message_relay.get_message_sender(message_id)
                    # Use conversation_id from ACK if provided, otherwise get from metadata
                    ack_conversation_id = conversation_id or message_relay.get_message_conversation(message_id) or ""
                    
                    # Acknowledge delivery via MessageRelayService
                    ack_success = message_relay.acknowledge_delivery(message_id, device_id)
                    
                    if ack_success:
                        # Forward ACK to sender (if sender is connected via WebSocket)
                        # Only forward if sender is different from recipient (not a self-message)
                        if sender_id and sender_id != device_id:
                            # Forward ACK to sender via WebSocket
                            ack_forward = {
                                "type": "ack",
                                "message_id": message_id_str,
                                "conversation_id": ack_conversation_id,
                                "status": "delivered",  # ACK indicates successful delivery
                            }
                            
                            # Send ACK to sender if connected
                            # Note: Race condition is handled by WebSocket manager's connection check
                            # If sender disconnects between check and send, send will fail gracefully
                            if websocket_manager.is_connected(sender_id):
                                websocket_manager.send_to_device(sender_id, json.dumps(ack_forward))
                                logger.debug(f"Forwarded ACK for message {message_id} to sender {sender_id}")
                            else:
                                logger.debug(f"Sender {sender_id} not connected, ACK not forwarded (will be available via REST)")
                        
                        logger.debug(f"Processed ACK for message {message_id} from {device_id}")
                    else:
                        logger.warning(f"Failed to process ACK for message {message_id} from {device_id}")
                else:
                    # Unknown message type - log for debugging
                    logger.debug(f"Received unknown WebSocket message from {device_id}: {message}")
                    
            except Exception as e:
                logger.warning(f"Failed to parse WebSocket message from {device_id}: {e}")
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for device {device_id}")
    except Exception as e:
        logger.error(f"WebSocket error for device {device_id}: {e}")
    finally:
        # Clean up connection
        await websocket_manager.disconnect(device_id)


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint for monitoring.
    
    Returns:
        Health status dictionary.
    """
    return {
        "status": "healthy",
        "service": "abiqua-backend",
        "version": "0.1.0",
    }


# ============================================================================
# Static File Serving (for Heroku deployment)
# ============================================================================

# Serve static files from frontend build directory (for Heroku deployment)
# Only mount if directory exists (frontend must be built first)
_frontend_dist_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "src", "ui", "dist")
if os.path.exists(_frontend_dist_path) and os.path.isdir(_frontend_dist_path):
    # Mount static files (JS, CSS, images, etc.)
    app.mount("/assets", StaticFiles(directory=os.path.join(_frontend_dist_path, "assets")), name="assets")
    
    # Serve index.html for all non-API routes (SPA routing)
    # This route must be defined LAST to avoid conflicts with API routes
    # FastAPI matches routes in order, so more specific routes (like /health, /api/*) are matched first
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """
        Serve frontend SPA for all non-API routes.
        
        This allows the React app to handle client-side routing.
        API routes are handled by FastAPI before this catch-all.
        """
        # Don't serve frontend for API routes, WebSocket routes, or health check
        if (full_path.startswith("api/") or 
            full_path.startswith("ws/") or 
            full_path == "health" or
            full_path.startswith("assets/")):
            raise HTTPException(status_code=404, detail="Not found")
        
        # Serve index.html for all other routes (SPA routing)
        index_path = os.path.join(_frontend_dist_path, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        else:
            raise HTTPException(status_code=404, detail="Frontend not built")
    
    logger.info(f"Static file serving enabled from: {_frontend_dist_path}")
else:
    logger.info("Frontend dist directory not found - static file serving disabled (frontend must be built)")


# ============================================================================
# Application Entry Point
# ============================================================================

def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        Configured FastAPI application instance.
    """
    return app


if __name__ == "__main__":
    import uvicorn
    
    # Run server for local development
    # TODO: Use environment variables for host/port configuration
    uvicorn.run(
        "src.backend.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes (development only)
        log_level="info",
    )
