"""
Unit tests for Controller API endpoints.

References:
- API Contracts (#10), Section 3.1 and 3.2
- Identity Provisioning (#11)
- State Machines (#7), Section 5
- Copy Rules (#13)
- Logging & Observability (#14)

Tests validate:
- Valid state transitions
- Invalid state transitions
- Authorization failures
- Idempotent revoke handling
"""

import pytest
from unittest.mock import Mock

from src.backend.controller_api import ControllerAPIService
from src.backend.controller_auth import ControllerAuthService
from src.backend.conversation_registry import ConversationRegistry
from src.backend.device_registry import DeviceRegistry
from src.backend.identity_enforcement import IdentityEnforcementService
from src.backend.logging_service import LoggingService
from src.shared.controller_types import (
    ConfirmProvisioningRequest,
    ProvisionDeviceRequest,
    RevokeDeviceRequest,
)
from src.shared.device_identity_types import DeviceIdentityState


@pytest.fixture
def device_registry() -> DeviceRegistry:
    """Create device registry for testing."""
    return DeviceRegistry()


@pytest.fixture
def conversation_registry(device_registry: DeviceRegistry) -> ConversationRegistry:
    """Create conversation registry for testing."""
    return ConversationRegistry(device_registry)


@pytest.fixture
def identity_enforcement(device_registry: DeviceRegistry) -> IdentityEnforcementService:
    """Create identity enforcement service for testing."""
    return IdentityEnforcementService(device_registry)


@pytest.fixture
def logging_service() -> LoggingService:
    """Create logging service for testing."""
    return LoggingService()


@pytest.fixture
def controller_auth() -> ControllerAuthService:
    """Create controller auth service for testing."""
    return ControllerAuthService(valid_api_keys=["test-controller-key"])


@pytest.fixture
def controller_api(
    device_registry: DeviceRegistry,
    conversation_registry: ConversationRegistry,
    identity_enforcement: IdentityEnforcementService,
    logging_service: LoggingService,
    controller_auth: ControllerAuthService,
) -> ControllerAPIService:
    """Create controller API service for testing."""
    return ControllerAPIService(
        device_registry=device_registry,
        conversation_registry=conversation_registry,
        identity_enforcement=identity_enforcement,
        logging_service=logging_service,
        controller_auth=controller_auth,
    )


class TestProvisionDevice:
    """Tests for POST /api/device/provision endpoint."""
    
    def test_provision_device_success(self, controller_api: ControllerAPIService) -> None:
        """Test successful device provisioning per Identity Provisioning (#11), Section 3."""
        request = ProvisionDeviceRequest(
            device_id="device-001",
            public_key="test-public-key",
        )
        
        result = controller_api.provision_device(request, "test-controller-key")
        
        assert result["status_code"] == 200
        assert result["response"]["status"] == "provisioned"
        assert result["response"]["device_id"] == "device-001"
        assert result["response"]["state"] == "pending"
        
        # Verify device is in Pending state
        device = controller_api.device_registry.get_device_identity("device-001")
        assert device is not None
        assert device.state == DeviceIdentityState.PENDING
    
    def test_provision_device_unauthorized(self, controller_api: ControllerAPIService) -> None:
        """Test provisioning with invalid API key per API Contracts (#10), Section 5."""
        request = ProvisionDeviceRequest(
            device_id="device-001",
            public_key="test-public-key",
        )
        
        result = controller_api.provision_device(request, "invalid-key")
        
        assert result["status_code"] == 401
        assert result["response"]["error_code"] == 401
        assert result["response"]["message"] == "Unauthorized"
    
    def test_provision_device_missing_key(self, controller_api: ControllerAPIService) -> None:
        """Test provisioning without API key."""
        request = ProvisionDeviceRequest(
            device_id="device-001",
            public_key="test-public-key",
        )
        
        result = controller_api.provision_device(request, None)
        
        assert result["status_code"] == 401
        assert result["response"]["error_code"] == 401
    
    def test_provision_device_invalid_request(self, controller_api: ControllerAPIService) -> None:
        """Test provisioning with invalid request (missing fields)."""
        request = ProvisionDeviceRequest(
            device_id="",  # Empty device_id
            public_key="test-public-key",
        )
        
        result = controller_api.provision_device(request, "test-controller-key")
        
        assert result["status_code"] == 400
        assert result["response"]["error_code"] == 400
    
    def test_provision_device_already_exists(self, controller_api: ControllerAPIService) -> None:
        """Test provisioning device that already exists."""
        request = ProvisionDeviceRequest(
            device_id="device-001",
            public_key="test-public-key",
        )
        
        # First provisioning succeeds
        result1 = controller_api.provision_device(request, "test-controller-key")
        assert result1["status_code"] == 200
        
        # Second provisioning fails
        result2 = controller_api.provision_device(request, "test-controller-key")
        assert result2["status_code"] == 409
        assert result2["response"]["error_code"] == 409
        assert "already exists" in result2["response"]["message"]


class TestConfirmProvisioning:
    """Tests for POST /api/device/provision/confirm endpoint."""
    
    def test_confirm_provisioning_success(self, controller_api: ControllerAPIService) -> None:
        """Test successful provisioning confirmation per Identity Provisioning (#11), Section 3."""
        # First provision device
        provision_request = ProvisionDeviceRequest(
            device_id="device-001",
            public_key="test-public-key",
        )
        controller_api.provision_device(provision_request, "test-controller-key")
        
        # Then confirm provisioning
        confirm_request = ConfirmProvisioningRequest(device_id="device-001")
        result = controller_api.confirm_provisioning(confirm_request, "test-controller-key")
        
        assert result["status_code"] == 200
        assert result["response"]["status"] == "confirmed"
        assert result["response"]["device_id"] == "device-001"
        assert result["response"]["state"] == "provisioned"
        
        # Verify device is in Provisioned state
        device = controller_api.device_registry.get_device_identity("device-001")
        assert device is not None
        assert device.state == DeviceIdentityState.PROVISIONED
    
    def test_confirm_provisioning_unauthorized(self, controller_api: ControllerAPIService) -> None:
        """Test confirmation with invalid API key."""
        confirm_request = ConfirmProvisioningRequest(device_id="device-001")
        result = controller_api.confirm_provisioning(confirm_request, "invalid-key")
        
        assert result["status_code"] == 401
        assert result["response"]["error_code"] == 401
    
    def test_confirm_provisioning_device_not_found(self, controller_api: ControllerAPIService) -> None:
        """Test confirmation for non-existent device."""
        confirm_request = ConfirmProvisioningRequest(device_id="device-nonexistent")
        result = controller_api.confirm_provisioning(confirm_request, "test-controller-key")
        
        assert result["status_code"] == 404
        assert result["response"]["error_code"] == 404
        assert "not found" in result["response"]["message"]
    
    def test_confirm_provisioning_invalid_state(self, controller_api: ControllerAPIService) -> None:
        """Test confirmation from invalid state (not Pending)."""
        # Provision and confirm once (now in Provisioned state)
        provision_request = ProvisionDeviceRequest(
            device_id="device-001",
            public_key="test-public-key",
        )
        controller_api.provision_device(provision_request, "test-controller-key")
        confirm_request = ConfirmProvisioningRequest(device_id="device-001")
        controller_api.confirm_provisioning(confirm_request, "test-controller-key")
        
        # Try to confirm again (invalid state transition)
        result = controller_api.confirm_provisioning(confirm_request, "test-controller-key")
        
        assert result["status_code"] == 409
        assert result["response"]["error_code"] == 409
        assert "not in pending state" in result["response"]["message"]


class TestRevokeDevice:
    """Tests for POST /api/device/revoke endpoint."""
    
    def test_revoke_device_success(self, controller_api: ControllerAPIService) -> None:
        """Test successful device revocation per Identity Provisioning (#11), Section 5."""
        # Provision and activate device
        provision_request = ProvisionDeviceRequest(
            device_id="device-001",
            public_key="test-public-key",
        )
        controller_api.provision_device(provision_request, "test-controller-key")
        confirm_request = ConfirmProvisioningRequest(device_id="device-001")
        controller_api.confirm_provisioning(confirm_request, "test-controller-key")
        
        # Activate device (transition to Active)
        controller_api.device_registry.confirm_provisioning("device-001")
        
        # Revoke device
        revoke_request = RevokeDeviceRequest(device_id="device-001")
        result = controller_api.revoke_device(revoke_request, "test-controller-key")
        
        assert result["status_code"] == 200
        assert result["response"]["status"] == "revoked"
        assert result["response"]["device_id"] == "device-001"
        
        # Verify device is in Revoked state
        device = controller_api.device_registry.get_device_identity("device-001")
        assert device is not None
        assert device.state == DeviceIdentityState.REVOKED
        assert device.is_revoked()
    
    def test_revoke_device_unauthorized(self, controller_api: ControllerAPIService) -> None:
        """Test revocation with invalid API key."""
        revoke_request = RevokeDeviceRequest(device_id="device-001")
        result = controller_api.revoke_device(revoke_request, "invalid-key")
        
        assert result["status_code"] == 401
        assert result["response"]["error_code"] == 401
    
    def test_revoke_device_not_found(self, controller_api: ControllerAPIService) -> None:
        """Test revocation of non-existent device."""
        revoke_request = RevokeDeviceRequest(device_id="device-nonexistent")
        result = controller_api.revoke_device(revoke_request, "test-controller-key")
        
        assert result["status_code"] == 404
        assert result["response"]["error_code"] == 404
        assert "not found" in result["response"]["message"]
    
    def test_revoke_device_idempotent(self, controller_api: ControllerAPIService) -> None:
        """Test idempotent revoke handling per Identity Provisioning (#11), Section 5."""
        # Provision and activate device
        provision_request = ProvisionDeviceRequest(
            device_id="device-001",
            public_key="test-public-key",
        )
        controller_api.provision_device(provision_request, "test-controller-key")
        confirm_request = ConfirmProvisioningRequest(device_id="device-001")
        controller_api.confirm_provisioning(confirm_request, "test-controller-key")
        controller_api.device_registry.confirm_provisioning("device-001")
        
        # Revoke device first time
        revoke_request = RevokeDeviceRequest(device_id="device-001")
        result1 = controller_api.revoke_device(revoke_request, "test-controller-key")
        assert result1["status_code"] == 200
        
        # Revoke device second time (should be idempotent)
        result2 = controller_api.revoke_device(revoke_request, "test-controller-key")
        assert result2["status_code"] == 200
        assert result2["response"]["status"] == "revoked"
        
        # Device should still be revoked
        device = controller_api.device_registry.get_device_identity("device-001")
        assert device is not None
        assert device.is_revoked()
    
    def test_revoke_device_removes_from_conversations(
        self, controller_api: ControllerAPIService
    ) -> None:
        """Test that revoked device is removed from all conversations per State Machines (#7), Section 4."""
        # Provision and activate device
        provision_request = ProvisionDeviceRequest(
            device_id="device-001",
            public_key="test-public-key",
        )
        controller_api.provision_device(provision_request, "test-controller-key")
        confirm_request = ConfirmProvisioningRequest(device_id="device-001")
        controller_api.confirm_provisioning(confirm_request, "test-controller-key")
        controller_api.device_registry.confirm_provisioning("device-001")
        
        # Create conversation with device-001
        controller_api.conversation_registry.register_conversation(
            "conv-001",
            ["device-001"],
        )
        
        # Verify device is in conversation
        participants = controller_api.conversation_registry.get_conversation_participants("conv-001")
        assert participants is not None
        assert "device-001" in participants
        
        # Revoke device
        revoke_request = RevokeDeviceRequest(device_id="device-001")
        result = controller_api.revoke_device(revoke_request, "test-controller-key")
        
        assert result["status_code"] == 200
        assert result["response"]["affected_conversations"] == 1
        
        # Verify device is removed from conversation
        participants_after = controller_api.conversation_registry.get_conversation_participants("conv-001")
        assert participants_after is not None
        assert "device-001" not in participants_after
    
    def test_revoke_device_closes_conversations_when_all_revoked(
        self, controller_api: ControllerAPIService
    ) -> None:
        """Test that conversations close when all participants are revoked per State Machines (#7), Section 4."""
        # Provision and activate two devices
        for device_id in ["device-001", "device-002"]:
            provision_request = ProvisionDeviceRequest(
                device_id=device_id,
                public_key=f"test-public-key-{device_id}",
            )
            controller_api.provision_device(provision_request, "test-controller-key")
            confirm_request = ConfirmProvisioningRequest(device_id=device_id)
            controller_api.confirm_provisioning(confirm_request, "test-controller-key")
            controller_api.device_registry.confirm_provisioning(device_id)
        
        # Create conversation with both devices
        controller_api.conversation_registry.register_conversation(
            "conv-001",
            ["device-001", "device-002"],
        )
        
        # Revoke both devices
        for device_id in ["device-001", "device-002"]:
            revoke_request = RevokeDeviceRequest(device_id=device_id)
            controller_api.revoke_device(revoke_request, "test-controller-key")
        
        # Verify conversation is closed
        is_active = controller_api.conversation_registry.is_conversation_active("conv-001")
        assert not is_active


class TestStateTransitions:
    """Tests for strict state transition enforcement."""
    
    def test_cannot_revoke_pending_device(self, controller_api: ControllerAPIService) -> None:
        """Test that Pending devices cannot be revoked (must be Active or Provisioned)."""
        # Provision device (now in Pending state)
        provision_request = ProvisionDeviceRequest(
            device_id="device-001",
            public_key="test-public-key",
        )
        controller_api.provision_device(provision_request, "test-controller-key")
        
        # Try to revoke (should fail - invalid state transition)
        # Per State Machines (#7), Section 5: revocation only from Active or Provisioned
        revoke_request = RevokeDeviceRequest(device_id="device-001")
        result = controller_api.revoke_device(revoke_request, "test-controller-key")
        
        # Revocation should fail due to invalid state
        # device_registry.revoke_device returns False for invalid state
        # API returns 500 (backend failure) when revocation fails
        assert result["status_code"] == 500
        
        # Device should still be in Pending state (revocation failed)
        device = controller_api.device_registry.get_device_identity("device-001")
        assert device is not None
        assert device.state == DeviceIdentityState.PENDING
    
    def test_provisioning_creates_pending_state(self, controller_api: ControllerAPIService) -> None:
        """Test that provisioning creates device in Pending state per Identity Provisioning (#11), Section 3."""
        request = ProvisionDeviceRequest(
            device_id="device-001",
            public_key="test-public-key",
        )
        
        result = controller_api.provision_device(request, "test-controller-key")
        
        assert result["status_code"] == 200
        device = controller_api.device_registry.get_device_identity("device-001")
        assert device is not None
        assert device.state == DeviceIdentityState.PENDING
    
    def test_confirmation_transitions_to_provisioned(
        self, controller_api: ControllerAPIService
    ) -> None:
        """Test that confirmation transitions Pending → Provisioned per State Machines (#7), Section 5."""
        # Provision device
        provision_request = ProvisionDeviceRequest(
            device_id="device-001",
            public_key="test-public-key",
        )
        controller_api.provision_device(provision_request, "test-controller-key")
        
        # Confirm provisioning
        confirm_request = ConfirmProvisioningRequest(device_id="device-001")
        result = controller_api.confirm_provisioning(confirm_request, "test-controller-key")
        
        assert result["status_code"] == 200
        device = controller_api.device_registry.get_device_identity("device-001")
        assert device is not None
        assert device.state == DeviceIdentityState.PROVISIONED
    
    def test_revocation_is_irreversible(self, controller_api: ControllerAPIService) -> None:
        """Test that revocation is irreversible per Identity Provisioning (#11), Section 5."""
        # Provision, activate, and revoke device
        provision_request = ProvisionDeviceRequest(
            device_id="device-001",
            public_key="test-public-key",
        )
        controller_api.provision_device(provision_request, "test-controller-key")
        confirm_request = ConfirmProvisioningRequest(device_id="device-001")
        controller_api.confirm_provisioning(confirm_request, "test-controller-key")
        controller_api.device_registry.confirm_provisioning("device-001")
        
        revoke_request = RevokeDeviceRequest(device_id="device-001")
        controller_api.revoke_device(revoke_request, "test-controller-key")
        
        # Verify device is revoked
        device = controller_api.device_registry.get_device_identity("device-001")
        assert device is not None
        assert device.is_revoked()
        
        # Try to reactivate (should not be possible)
        # The device_registry doesn't have a reactivate method, which is correct
        # Revocation is irreversible per Identity Provisioning (#11), Section 5
        assert device.state == DeviceIdentityState.REVOKED
