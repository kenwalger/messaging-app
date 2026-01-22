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
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import UUID, uuid4

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
from fastapi.responses import JSONResponse

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
    _device_registry = DeviceRegistry()
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

if is_development:
    # Permissive CORS for local development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
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
    logger.info("CORS enabled for local development (localhost:5173, 127.0.0.1:5173)")
else:
    # Production: Strict CORS (no middleware added - will reject cross-origin requests)
    logger.info("CORS disabled - production mode (strict security)")

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

@app.post("/api/conversation/create")
async def create_conversation(
    participants: List[str],
    device_id: str = Depends(get_device_id),
) -> JSONResponse:
    """
    Create conversation endpoint per API Contracts (#10) and Functional Spec (#6), Section 4.1.
    """
    conversation_service = get_conversation_service()
    result = conversation_service.create_conversation(device_id, participants)
    
    status_code = result.get("status_code", 200)
    return JSONResponse(content=result, status_code=status_code)


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
    """
    # Extract required request fields per API Contracts (#10), Section 3.3
    message_id_str = request.get("message_id")
    conversation_id = request.get("conversation_id", "")
    payload = request.get("payload", "")  # Encrypted payload (base64 or hex string)
    timestamp_str = request.get("timestamp")  # ISO timestamp string
    expiration = request.get("expiration")  # ISO timestamp string (optional, derived from timestamp if not provided)
    
    # Validate required fields
    if not message_id_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request: message_id is required",
        )
    
    if not conversation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request: conversation_id is required",
        )
    
    if not timestamp_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request: timestamp is required",
        )
    
    # Parse and validate message_id
    try:
        message_id = UUID(message_id_str)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid message_id: {e}",
        )
    
    # Parse and validate timestamp (reject expired)
    try:
        message_timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid timestamp format: {e}",
        )
    
    # Reject expired timestamps and future timestamps (with clock skew tolerance)
    now = utc_now()
    clock_skew = timedelta(minutes=CLOCK_SKEW_TOLERANCE_MINUTES)
    if message_timestamp < now - clock_skew:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request: timestamp is expired",
        )
    if message_timestamp > now + clock_skew:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request: timestamp is too far in the future",
        )
    
    # Validate payload is a string
    if not isinstance(payload, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request: payload must be a string",
        )
    
    # Validate payload is not empty
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request: payload cannot be empty",
        )
    
    # Convert payload to bytes (assuming base64 or hex encoding)
    try:
        encrypted_payload = base64.b64decode(payload)
    except Exception:
        # Try hex decoding as fallback
        try:
            encrypted_payload = bytes.fromhex(payload)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid payload encoding: {e}",
            )
    
    # Enforce payload size ≤ 50KB
    payload_size_kb = len(encrypted_payload) / 1024
    if payload_size_kb > MAX_MESSAGE_PAYLOAD_SIZE_KB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: payload size ({payload_size_kb:.1f}KB) exceeds maximum ({MAX_MESSAGE_PAYLOAD_SIZE_KB}KB)",
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
    if not conversation_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    
    # If conversation exists but is not active, return 400
    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request: conversation is not active",
        )
    
    # Authorization check: Verify sender is a participant in the conversation
    if device_id not in participants:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid request: sender is not a participant in this conversation",
        )
    
    # Exclude sender from recipients (they shouldn't receive their own message)
    recipients = [p for p in participants if p != device_id]
    
    if not recipients:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request: no recipients available (conversation has only sender)",
        )
    
    # Parse expiration timestamp (use provided or derive from timestamp + default expiration)
    if expiration:
        try:
            expiration_timestamp = datetime.fromisoformat(expiration.replace("Z", "+00:00"))
        except (ValueError, AttributeError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid expiration timestamp: {e}",
            )
    else:
        # Derive expiration from timestamp + default expiration days
        expiration_timestamp = message_timestamp + timedelta(days=DEFAULT_MESSAGE_EXPIRATION_DAYS)
    
    # Log message send attempt (metadata only, no content) per Logging & Observability (#14)
    logging_service = get_logging_service()
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
    
    # Return 202 Accepted per API Contracts (#10), Section 3.3
    return JSONResponse(
        content={
            "status": "accepted",
            "message_id": str(message_id),
        },
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
    
    # Development mode: Auto-provision devices for local development convenience
    # In production, devices must be provisioned via Controller API first
    if is_development and not device_registry.is_device_active(device_id):
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
            # Still not active - close connection
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    elif not device_registry.is_device_active(device_id):
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
