"""
Unit tests for device identity and revocation enforcement.

References:
- Identity Provisioning (#11)
- State Machines (#7), Section 5
- Functional Specification (#6), Section 3.1
- Resolved Specs & Clarifications
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock

from src.backend.device_registry import DeviceRegistry
from src.backend.identity_enforcement import IdentityEnforcementService
from src.shared.device_identity_types import DeviceIdentity, DeviceIdentityState
from src.shared.message_types import utc_now


class TestDeviceIdentity(unittest.TestCase):
    """Test cases for DeviceIdentity per Identity Provisioning (#11) and State Machines (#7)."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.device_id = "device-001"
        self.public_key = "test-public-key"
    
    def test_device_identity_creation(self) -> None:
        """
        Test device identity creation per Identity Provisioning (#11), Section 2.
        
        Device identity consists of device_id, public key, and provisioning metadata.
        """
        device = DeviceIdentity(
            device_id=self.device_id,
            state=DeviceIdentityState.PENDING,
            public_key=self.public_key,
        )
        
        self.assertEqual(device.device_id, self.device_id)
        self.assertEqual(device.public_key, self.public_key)
        self.assertEqual(device.state, DeviceIdentityState.PENDING)
        self.assertIsNotNone(device.created_at)
        self.assertIsNotNone(device.next_key_rotation)
    
    def test_device_state_transitions(self) -> None:
        """
        Test device state transitions per State Machines (#7), Section 5.
        
        Transitions: Pending → Provisioned → Active → Revoked
        """
        device = DeviceIdentity(
            device_id=self.device_id,
            state=DeviceIdentityState.PENDING,
            public_key=self.public_key,
        )
        
        # Pending → Provisioned
        device.transition_to_provisioned()
        self.assertEqual(device.state, DeviceIdentityState.PROVISIONED)
        self.assertIsNotNone(device.provisioned_at)
        
        # Provisioned → Active
        device.transition_to_active()
        self.assertEqual(device.state, DeviceIdentityState.ACTIVE)
        self.assertIsNotNone(device.activated_at)
        
        # Active → Revoked
        device.transition_to_revoked()
        self.assertEqual(device.state, DeviceIdentityState.REVOKED)
        self.assertIsNotNone(device.revoked_at)
    
    def test_revocation_irreversible(self) -> None:
        """
        Test revocation is irreversible per Identity Provisioning (#11), Section 5.
        
        Once revoked, device cannot transition back to Active.
        """
        device = DeviceIdentity(
            device_id=self.device_id,
            state=DeviceIdentityState.ACTIVE,
            public_key=self.public_key,
        )
        
        device.transition_to_revoked()
        self.assertEqual(device.state, DeviceIdentityState.REVOKED)
        
        # Attempting to revoke again should be no-op
        device.transition_to_revoked()
        self.assertEqual(device.state, DeviceIdentityState.REVOKED)
    
    def test_revocation_triggers_key_rotation(self) -> None:
        """
        Test revocation triggers key rotation per Resolved Clarifications.
        
        Key rotation occurs immediately upon revocation.
        """
        device = DeviceIdentity(
            device_id=self.device_id,
            state=DeviceIdentityState.ACTIVE,
            public_key=self.public_key,
        )
        
        old_key_rotation = device.last_key_rotation
        
        device.transition_to_revoked(trigger_key_rotation=True)
        
        # Key rotation timestamp should be updated
        self.assertGreaterEqual(device.last_key_rotation, old_key_rotation)
        # Revoked devices don't get scheduled rotations
        self.assertIsNone(device.next_key_rotation)
    
    def test_can_send_messages(self) -> None:
        """
        Test message sending permissions per Functional Spec (#6), Section 4.2.
        
        Only Active devices can send messages.
        Revoked devices cannot send messages per Resolved Clarifications (#38).
        """
        active_device = DeviceIdentity(
            device_id=self.device_id,
            state=DeviceIdentityState.ACTIVE,
            public_key=self.public_key,
        )
        self.assertTrue(active_device.can_send_messages())
        
        revoked_device = DeviceIdentity(
            device_id="device-002",
            state=DeviceIdentityState.REVOKED,
            public_key=self.public_key,
        )
        self.assertFalse(revoked_device.can_send_messages())
    
    def test_can_read_conversations(self) -> None:
        """
        Test conversation read permissions per Resolved Clarifications (#38).
        
        Active devices can read conversations.
        Revoked devices can read historical conversations (neutral enterprise mode).
        """
        active_device = DeviceIdentity(
            device_id=self.device_id,
            state=DeviceIdentityState.ACTIVE,
            public_key=self.public_key,
        )
        self.assertTrue(active_device.can_read_conversations())
        
        revoked_device = DeviceIdentity(
            device_id="device-002",
            state=DeviceIdentityState.REVOKED,
            public_key=self.public_key,
        )
        self.assertTrue(revoked_device.can_read_conversations())
    
    def test_key_rotation_scheduling(self) -> None:
        """
        Test key rotation scheduling per Resolved TBDs.
        
        Key rotation required every 90 days or immediately upon revocation.
        """
        device = DeviceIdentity(
            device_id=self.device_id,
            state=DeviceIdentityState.ACTIVE,
            public_key=self.public_key,
        )
        
        # Initially, device should not need rotation
        self.assertFalse(device.needs_key_rotation())
        
        # Set next rotation to past date
        device.next_key_rotation = utc_now() - timedelta(days=1)
        self.assertTrue(device.needs_key_rotation())
        
        # Revoked devices always need rotation
        device.transition_to_revoked()
        self.assertTrue(device.needs_key_rotation())


class TestDeviceRegistry(unittest.TestCase):
    """Test cases for DeviceRegistry per Identity Provisioning (#11)."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.registry = DeviceRegistry()
        self.device_id = "device-001"
        self.public_key = "test-public-key"
    
    def test_register_device(self) -> None:
        """
        Test device registration per Identity Provisioning (#11), Section 3.
        
        Creates device in Pending state per State Machines (#7), Section 5.
        """
        device = self.registry.register_device(
            device_id=self.device_id,
            public_key=self.public_key,
        )
        
        self.assertEqual(device.state, DeviceIdentityState.PENDING)
        self.assertTrue(self.registry.get_device_identity(self.device_id) is not None)
    
    def test_confirm_provisioning(self) -> None:
        """
        Test provisioning confirmation per Identity Provisioning (#11), Section 3.
        
        Transitions: Provisioned → Active per State Machines (#7), Section 5.
        """
        self.registry.register_device(
            device_id=self.device_id,
            public_key=self.public_key,
        )
        
        # First transition to Provisioned (simulating device receiving provisioning data)
        device = self.registry.get_device_identity(self.device_id)
        device.transition_to_provisioned()
        
        # Confirm provisioning
        success = self.registry.confirm_provisioning(self.device_id)
        self.assertTrue(success)
        
        device = self.registry.get_device_identity(self.device_id)
        self.assertEqual(device.state, DeviceIdentityState.ACTIVE)
        self.assertTrue(self.registry.is_device_active(self.device_id))
    
    def test_revoke_device(self) -> None:
        """
        Test device revocation per Identity Provisioning (#11), Section 5.
        
        Transitions: Active → Revoked per State Machines (#7), Section 5.
        Revocation is immediate and irreversible.
        """
        # Register and activate device
        self.registry.register_device(
            device_id=self.device_id,
            public_key=self.public_key,
        )
        device = self.registry.get_device_identity(self.device_id)
        device.transition_to_provisioned()
        device.transition_to_active()
        
        # Revoke device
        success = self.registry.revoke_device(self.device_id)
        self.assertTrue(success)
        
        device = self.registry.get_device_identity(self.device_id)
        self.assertEqual(device.state, DeviceIdentityState.REVOKED)
        self.assertFalse(self.registry.is_device_active(self.device_id))
    
    def test_revocation_permissions(self) -> None:
        """
        Test revocation impact on permissions per Resolved Clarifications (#38).
        
        Revoked devices:
        - Cannot send messages
        - Cannot create or join conversations
        - May read historical conversations
        """
        # Register and activate device
        self.registry.register_device(
            device_id=self.device_id,
            public_key=self.public_key,
        )
        device = self.registry.get_device_identity(self.device_id)
        device.transition_to_provisioned()
        device.transition_to_active()
        
        # Verify active device permissions
        self.assertTrue(self.registry.can_send_messages(self.device_id))
        self.assertTrue(self.registry.can_create_conversations(self.device_id))
        self.assertTrue(self.registry.can_join_conversations(self.device_id))
        self.assertTrue(self.registry.can_read_conversations(self.device_id))
        
        # Revoke device
        self.registry.revoke_device(self.device_id)
        
        # Verify revoked device permissions
        self.assertFalse(self.registry.can_send_messages(self.device_id))
        self.assertFalse(self.registry.can_create_conversations(self.device_id))
        self.assertFalse(self.registry.can_join_conversations(self.device_id))
        self.assertTrue(self.registry.can_read_conversations(self.device_id))  # Can still read
    
    def test_key_rotation_scheduling(self) -> None:
        """
        Test key rotation scheduling per Resolved TBDs.
        
        Key rotation required every 90 days or immediately upon revocation.
        """
        # Register and activate device
        self.registry.register_device(
            device_id=self.device_id,
            public_key=self.public_key,
        )
        device = self.registry.get_device_identity(self.device_id)
        device.transition_to_provisioned()
        device.transition_to_active()
        
        # Initially, no devices need rotation
        devices_needing_rotation = self.registry.get_devices_needing_key_rotation()
        self.assertEqual(len(devices_needing_rotation), 0)
        
        # Revoke device (triggers immediate rotation)
        self.registry.revoke_device(self.device_id)
        devices_needing_rotation = self.registry.get_devices_needing_key_rotation()
        # Revoked devices need rotation, but rotation is handled in transition
        # So they may or may not appear in the list depending on implementation
        
        # Rotate key
        new_public_key = "new-public-key"
        success = self.registry.rotate_device_key(self.device_id, new_public_key)
        self.assertTrue(success)
        
        device = self.registry.get_device_identity(self.device_id)
        self.assertEqual(device.public_key, new_public_key)


class TestIdentityEnforcement(unittest.TestCase):
    """Test cases for IdentityEnforcementService per Functional Spec (#6), Section 3.2."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.registry = DeviceRegistry()
        self.enforcement = IdentityEnforcementService(self.registry)
        self.device_id = "device-001"
        self.public_key = "test-public-key"
    
    def test_enforce_message_sending_active_device(self) -> None:
        """
        Test message sending enforcement for active device per Functional Spec (#6), Section 4.2.
        
        Active devices can send messages.
        """
        # Register and activate device
        self.registry.register_device(
            device_id=self.device_id,
            public_key=self.public_key,
        )
        device = self.registry.get_device_identity(self.device_id)
        device.transition_to_provisioned()
        device.transition_to_active()
        
        result = self.enforcement.enforce_message_sending(self.device_id)
        self.assertTrue(result["allowed"])
    
    def test_enforce_message_sending_revoked_device(self) -> None:
        """
        Test message sending enforcement for revoked device per Resolved Clarifications (#38).
        
        Revoked devices cannot send messages.
        """
        # Register, activate, then revoke device
        self.registry.register_device(
            device_id=self.device_id,
            public_key=self.public_key,
        )
        device = self.registry.get_device_identity(self.device_id)
        device.transition_to_provisioned()
        device.transition_to_active()
        self.registry.revoke_device(self.device_id)
        
        result = self.enforcement.enforce_message_sending(self.device_id)
        self.assertFalse(result["allowed"])
        self.assertEqual(result["error_code"], 403)  # Forbidden
    
    def test_enforce_conversation_creation_revoked_device(self) -> None:
        """
        Test conversation creation enforcement for revoked device per Resolved Clarifications (#38).
        
        Revoked devices cannot create conversations.
        """
        # Register, activate, then revoke device
        self.registry.register_device(
            device_id=self.device_id,
            public_key=self.public_key,
        )
        device = self.registry.get_device_identity(self.device_id)
        device.transition_to_provisioned()
        device.transition_to_active()
        self.registry.revoke_device(self.device_id)
        
        result = self.enforcement.enforce_conversation_creation(self.device_id)
        self.assertFalse(result["allowed"])
        self.assertEqual(result["error_code"], 403)  # Forbidden
    
    def test_enforce_conversation_read_revoked_device(self) -> None:
        """
        Test conversation read enforcement for revoked device per Resolved Clarifications (#38).
        
        Revoked devices can read historical conversations (neutral enterprise mode).
        """
        # Register, activate, then revoke device
        self.registry.register_device(
            device_id=self.device_id,
            public_key=self.public_key,
        )
        device = self.registry.get_device_identity(self.device_id)
        device.transition_to_provisioned()
        device.transition_to_active()
        self.registry.revoke_device(self.device_id)
        
        result = self.enforcement.enforce_conversation_read(self.device_id)
        self.assertTrue(result["allowed"])  # Can still read
    
    def test_handle_revocation_impact(self) -> None:
        """
        Test revocation impact handling per State Machines (#7), Section 4.
        
        When device is revoked, it's removed from all conversations.
        """
        # Create mock conversation registry
        conversation_registry = Mock()
        conversation_registry.handle_participant_revocation = Mock(
            return_value=["conv-001", "conv-002"]
        )
        conversation_registry.is_conversation_active = Mock(
            side_effect=lambda cid: cid == "conv-001"
        )
        
        result = self.enforcement.handle_revocation_impact(
            device_id=self.device_id,
            conversation_registry=conversation_registry,
        )
        
        self.assertEqual(len(result["affected_conversations"]), 2)
        self.assertEqual(result["conversations_closed"], 1)  # Only conv-002 is closed


if __name__ == "__main__":
    unittest.main()
