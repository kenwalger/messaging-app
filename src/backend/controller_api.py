"""
Controller API endpoints for device provisioning and revocation.

References:
- API Contracts (#10), Section 3.1 and 3.2
- Identity Provisioning (#11)
- State Machines (#7), Section 5
- Copy Rules (#13)
- Logging & Observability (#14)
- Resolved Specs & Clarifications

Implements:
- POST /api/device/provision
- POST /api/device/provision/confirm
- POST /api/device/revoke

All endpoints:
- Validate controller authorization
- Perform strict state transitions only
- Return client-safe DTOs
- Use neutral copy per Copy Rules (#13)
- Emit audit events per Logging & Observability (#14)
"""

import logging
from typing import Any, Dict, Optional

from src.backend.controller_auth import ControllerAuthService
from src.backend.conversation_registry import ConversationRegistry
from src.backend.device_registry import DeviceRegistry
from src.backend.identity_enforcement import IdentityEnforcementService
from src.backend.logging_service import LoggingService
from src.shared.constants import (
    ERROR_MESSAGING_DISABLED,
    HEADER_CONTROLLER_KEY,
    LOG_EVENT_DEVICE_PROVISIONED,
    LOG_EVENT_DEVICE_REVOKED,
)
from src.shared.controller_types import (
    ConfirmProvisioningRequest,
    ConfirmProvisioningResponse,
    ProvisionDeviceRequest,
    ProvisionDeviceResponse,
    RevokeDeviceRequest,
    RevokeDeviceResponse,
)
from src.shared.device_identity_types import DeviceIdentityState

# Configure logging per Logging & Observability (#14)
# Note: No device keys or sensitive data logged per Data Classification (#8)
logger = logging.getLogger(__name__)


class ControllerAPIService:
    """
    Controller API service per API Contracts (#10), Section 3.1 and 3.2.
    
    Handles device provisioning and revocation operations.
    Only Controllers can initiate provisioning and revocation per Identity Provisioning (#11).
    """
    
    def __init__(
        self,
        device_registry: DeviceRegistry,
        conversation_registry: ConversationRegistry,
        identity_enforcement: IdentityEnforcementService,
        logging_service: LoggingService,
        controller_auth: ControllerAuthService,
    ) -> None:
        """
        Initialize controller API service.
        
        Args:
            device_registry: Device registry for identity management.
            conversation_registry: Conversation registry for revocation impact handling.
            identity_enforcement: Identity enforcement service for revocation handling.
            logging_service: Logging service for audit events.
            controller_auth: Controller authentication service.
        """
        self.device_registry = device_registry
        self.conversation_registry = conversation_registry
        self.identity_enforcement = identity_enforcement
        self.logging_service = logging_service
        self.controller_auth = controller_auth
    
    def provision_device(
        self,
        request: ProvisionDeviceRequest,
        controller_key: Optional[str],
    ) -> Dict[str, Any]:
        """
        Provision device endpoint per API Contracts (#10), Section 3.1.
        
        Endpoint: POST /api/device/provision
        Creates device in Pending state per Identity Provisioning (#11), Section 3.
        
        Args:
            request: Provision device request with device_id and public_key.
            controller_key: Controller API key from X-Controller-Key header.
        
        Returns:
            Response dictionary with status code and response data.
            Status codes: 200 (success), 400 (invalid request), 401 (unauthorized), 409 (device already exists).
        """
        # Validate controller authorization
        if not self.controller_auth.validate_controller_key(controller_key):
            return {
                "status_code": 401,
                "response": {
                    "status": "error",
                    "error_code": 401,
                    "message": "Unauthorized",
                    "api_version": "v1",
                },
            }
        
        # Validate request
        if not request.device_id or not request.public_key:
            return {
                "status_code": 400,
                "response": {
                    "status": "error",
                    "error_code": 400,
                    "message": "Invalid request",
                    "api_version": "v1",
                },
            }
        
        # Check if device already exists
        existing_device = self.device_registry.get_device_identity(request.device_id)
        if existing_device is not None:
            return {
                "status_code": 409,
                "response": {
                    "status": "error",
                    "error_code": 409,
                    "message": "Device already exists",
                    "api_version": "v1",
                },
            }
        
        # Register device in Pending state per Identity Provisioning (#11), Section 3
        try:
            device = self.device_registry.register_device(
                device_id=request.device_id,
                public_key=request.public_key,
                controller_id=None,  # Could extract from controller_key if needed
            )
        except ValueError as e:
            logger.warning(f"Failed to register device {request.device_id}: {e}")
            return {
                "status_code": 400,
                "response": {
                    "status": "error",
                    "error_code": 400,
                    "message": "Invalid request",
                    "api_version": "v1",
                },
            }
        
        # Emit audit event per Logging & Observability (#14)
        from src.shared.logging_types import LogEventType
        self.logging_service.log_audit_event(
            event_type=LogEventType.DEVICE_PROVISIONED,
            event_data={
                "state": DeviceIdentityState.PENDING.value,
                "controller_operation": "provision",
            },
            actor_id=request.device_id,
        )
        
        # Return success response
        response = ProvisionDeviceResponse(
            status="provisioned",
            device_id=device.device_id,
            state=device.state.value,
        )
        
        return {
            "status_code": 200,
            "response": response.to_dict(),
        }
    
    def confirm_provisioning(
        self,
        request: ConfirmProvisioningRequest,
        controller_key: Optional[str],
    ) -> Dict[str, Any]:
        """
        Confirm device provisioning endpoint per Identity Provisioning (#11), Section 3.
        
        Endpoint: POST /api/device/provision/confirm
        Transitions: Pending → Provisioned per State Machines (#7), Section 5.
        
        Args:
            request: Confirm provisioning request with device_id.
            controller_key: Controller API key from X-Controller-Key header.
        
        Returns:
            Response dictionary with status code and response data.
            Status codes: 200 (success), 400 (invalid request), 401 (unauthorized), 404 (device not found), 409 (invalid state).
        """
        # Validate controller authorization
        if not self.controller_auth.validate_controller_key(controller_key):
            return {
                "status_code": 401,
                "response": {
                    "status": "error",
                    "error_code": 401,
                    "message": "Unauthorized",
                    "api_version": "v1",
                },
            }
        
        # Validate request
        if not request.device_id:
            return {
                "status_code": 400,
                "response": {
                    "status": "error",
                    "error_code": 400,
                    "message": "Invalid request",
                    "api_version": "v1",
                },
            }
        
        # Get device
        device = self.device_registry.get_device_identity(request.device_id)
        if device is None:
            return {
                "status_code": 404,
                "response": {
                    "status": "error",
                    "error_code": 404,
                    "message": "Device not found",
                    "api_version": "v1",
                },
            }
        
        # Validate state transition: Pending → Provisioned
        if device.state != DeviceIdentityState.PENDING:
            return {
                "status_code": 409,
                "response": {
                    "status": "error",
                    "error_code": 409,
                    "message": "Device not in pending state",
                    "api_version": "v1",
                },
            }
        
        # Transition to Provisioned state per State Machines (#7), Section 5
        success = self.device_registry.provision_device(request.device_id)
        if not success:
            return {
                "status_code": 500,
                "response": {
                    "status": "error",
                    "error_code": 500,
                    "message": "Backend failure",
                    "api_version": "v1",
                },
            }
        
        # Get updated device state
        updated_device = self.device_registry.get_device_identity(request.device_id)
        
        # Emit audit event per Logging & Observability (#14)
        from src.shared.logging_types import LogEventType
        self.logging_service.log_audit_event(
            event_type=LogEventType.DEVICE_PROVISIONED,
            event_data={
                "state": DeviceIdentityState.PROVISIONED.value,
                "controller_operation": "confirm_provisioning",
            },
            actor_id=request.device_id,
        )
        
        # Return success response
        response = ConfirmProvisioningResponse(
            status="confirmed",
            device_id=request.device_id,
            state=updated_device.state.value if updated_device else None,
        )
        
        return {
            "status_code": 200,
            "response": response.to_dict(),
        }
    
    def revoke_device(
        self,
        request: RevokeDeviceRequest,
        controller_key: Optional[str],
    ) -> Dict[str, Any]:
        """
        Revoke device endpoint per API Contracts (#10), Section 3.2.
        
        Endpoint: POST /api/device/revoke
        Revocation is immediate and irreversible per Identity Provisioning (#11), Section 5.
        
        Revoked devices:
        - Are removed from all conversations
        - Enter neutral enterprise mode (read-only)
        - No reactivation allowed
        
        Args:
            request: Revoke device request with device_id.
            controller_key: Controller API key from X-Controller-Key header.
        
        Returns:
            Response dictionary with status code and response data.
            Status codes: 200 (success), 400 (invalid request), 401 (unauthorized), 404 (device not found).
        """
        # Validate controller authorization
        if not self.controller_auth.validate_controller_key(controller_key):
            return {
                "status_code": 401,
                "response": {
                    "status": "error",
                    "error_code": 401,
                    "message": "Unauthorized",
                    "api_version": "v1",
                },
            }
        
        # Validate request
        if not request.device_id:
            return {
                "status_code": 400,
                "response": {
                    "status": "error",
                    "error_code": 400,
                    "message": "Invalid request",
                    "api_version": "v1",
                },
            }
        
        # Get device
        device = self.device_registry.get_device_identity(request.device_id)
        if device is None:
            return {
                "status_code": 404,
                "response": {
                    "status": "error",
                    "error_code": 404,
                    "message": "Device not found",
                    "api_version": "v1",
                },
            }
        
        # Check if already revoked (idempotent)
        if device.is_revoked():
            # Already revoked, return success with current state
            affected = self.identity_enforcement.handle_revocation_impact(
                request.device_id,
                self.conversation_registry,
            )
            
            response = RevokeDeviceResponse(
                status="revoked",
                device_id=request.device_id,
                affected_conversations=len(affected.get("affected_conversations", [])),
                conversations_closed=affected.get("conversations_closed", 0),
            )
            
            return {
                "status_code": 200,
                "response": response.to_dict(),
            }
        
        # Revoke device per Identity Provisioning (#11), Section 5
        success = self.device_registry.revoke_device(
            device_id=request.device_id,
            controller_id=None,  # Could extract from controller_key if needed
        )
        
        if not success:
            return {
                "status_code": 500,
                "response": {
                    "status": "error",
                    "error_code": 500,
                    "message": "Backend failure",
                    "api_version": "v1",
                },
            }
        
        # Handle revocation impact: remove from conversations per State Machines (#7), Section 4
        impact = self.identity_enforcement.handle_revocation_impact(
            request.device_id,
            self.conversation_registry,
        )
        
        # Emit audit event per Logging & Observability (#14)
        from src.shared.logging_types import LogEventType
        self.logging_service.log_audit_event(
            event_type=LogEventType.DEVICE_REVOKED,
            event_data={
                "state": DeviceIdentityState.REVOKED.value,
                "controller_operation": "revoke",
                "affected_conversations": len(impact.get("affected_conversations", [])),
                "conversations_closed": impact.get("conversations_closed", 0),
            },
            actor_id=request.device_id,
        )
        
        # Return success response
        response = RevokeDeviceResponse(
            status="revoked",
            device_id=request.device_id,
            affected_conversations=len(impact.get("affected_conversations", [])),
            conversations_closed=impact.get("conversations_closed", 0),
        )
        
        return {
            "status_code": 200,
            "response": response.to_dict(),
        }
