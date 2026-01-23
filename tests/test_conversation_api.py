"""
Unit tests for backend conversation API service.

References:
- Functional Specification (#6), Section 4.1
- State Machines (#7), Section 4
- API Contracts (#10)
- Identity Provisioning (#11)
- Resolved Specs & Clarifications
"""

import unittest
from unittest.mock import Mock
from uuid import uuid4

from src.backend.conversation_api import ConversationService
from src.backend.conversation_registry import ConversationRegistry
from src.backend.conversation_store import InMemoryConversationStore
from src.shared.constants import MAX_GROUP_SIZE
from src.shared.conversation_types import ConversationState


class TestConversationAPI(unittest.TestCase):
    """Test cases for ConversationService per Functional Spec (#6) and State Machines (#7)."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.device_registry = Mock()
        self.device_registry.is_device_active = Mock(return_value=True)
        self.log_service = Mock()
        
        # Create conversation registry with in-memory store for tests
        store = InMemoryConversationStore()
        self.conversation_registry = ConversationRegistry(
            self.device_registry,
            conversation_store=store,
            demo_mode=True,
        )
        
        # Create conversation service
        self.service = ConversationService(
            conversation_registry=self.conversation_registry,
            device_registry=self.device_registry,
            log_service=self.log_service,
        )
    
    def test_create_conversation_success(self) -> None:
        """
        Test conversation creation API per Functional Spec (#6), Section 4.1.
        
        Only provisioned devices may create conversations per Identity Provisioning (#11).
        """
        device_id = "device-001"
        participants = [device_id, "device-002", "device-003"]
        
        response = self.service.create_conversation(
            device_id=device_id,
            participants=participants,
        )
        
        # Verify success response
        self.assertEqual(response["status"], "success")
        self.assertIn("conversation_id", response)
        self.assertEqual(response["state"], ConversationState.ACTIVE.value)
        self.assertEqual(len(response["participants"]), 3)
        
        # Verify conversation registered
        registered_participants = self.conversation_registry.get_conversation_participants(
            response["conversation_id"]
        )
        self.assertIsNotNone(registered_participants)
        self.assertEqual(len(registered_participants), 3)
    
    def test_create_conversation_revoked_device(self) -> None:
        """
        Test conversation creation with revoked device per Identity Provisioning (#11).
        
        Revoked devices cannot create conversations.
        """
        device_id = "revoked-device"
        self.device_registry.is_device_active = Mock(return_value=False)
        
        participants = [device_id, "device-002"]
        
        response = self.service.create_conversation(
            device_id=device_id,
            participants=participants,
        )
        
        # Verify error response
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["error_code"], 403)
        self.assertEqual(response["message"], "Device not authorized")
    
    def test_create_conversation_max_group_size(self) -> None:
        """
        Test conversation creation with max group size per Resolved TBDs.
        
        Max 50 participants per conversation.
        """
        device_id = "device-001"
        participants = [f"device-{i:03d}" for i in range(MAX_GROUP_SIZE + 1)]
        participants[0] = device_id
        
        response = self.service.create_conversation(
            device_id=device_id,
            participants=participants,
        )
        
        # Verify error response
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["error_code"], 400)
        self.assertIn("max group size", response["message"])
    
    def test_create_conversation_invalid_participants(self) -> None:
        """
        Test conversation creation with invalid participants per Identity Provisioning (#11).
        
        All participants must be provisioned devices.
        """
        device_id = "device-001"
        self.device_registry.is_device_active = Mock(
            side_effect=lambda did: did != "revoked-device"
        )
        
        participants = [device_id, "device-002", "revoked-device"]
        
        response = self.service.create_conversation(
            device_id=device_id,
            participants=participants,
        )
        
        # Verify error response
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["error_code"], 400)
        self.assertIn("provisioned devices", response["message"])
    
    def test_join_conversation_success(self) -> None:
        """
        Test join conversation API per State Machines (#7), Section 4.
        
        Only provisioned devices may join conversations per Identity Provisioning (#11).
        """
        # Create conversation
        device_id = "device-001"
        conv_id = str(uuid4())
        self.service.create_conversation(
            device_id=device_id,
            participants=[device_id, "device-002"],
            conversation_id=conv_id,
        )
        
        # Join conversation
        new_device = "device-003"
        response = self.service.join_conversation(
            device_id=new_device,
            conversation_id=conv_id,
        )
        
        # Verify success response
        self.assertEqual(response["status"], "success")
        
        # Verify participant added
        participants = self.conversation_registry.get_conversation_participants(conv_id)
        self.assertIsNotNone(participants)
        self.assertIn(new_device, participants)
    
    def test_join_conversation_revoked_device(self) -> None:
        """
        Test join conversation with revoked device per Identity Provisioning (#11).
        
        Revoked devices cannot join conversations.
        """
        # Create conversation
        device_id = "device-001"
        conv_id = str(uuid4())
        self.service.create_conversation(
            device_id=device_id,
            participants=[device_id],
            conversation_id=conv_id,
        )
        
        # Attempt to join with revoked device
        revoked_device = "revoked-device"
        self.device_registry.is_device_active = Mock(
            side_effect=lambda did: did != revoked_device
        )
        
        response = self.service.join_conversation(
            device_id=revoked_device,
            conversation_id=conv_id,
        )
        
        # Verify error response
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["error_code"], 403)
        self.assertEqual(response["message"], "Device not authorized")
    
    def test_join_conversation_max_group_size(self) -> None:
        """
        Test join conversation with max group size per Resolved TBDs.
        
        Cannot join if conversation has reached max group size (50).
        """
        # Create conversation with max participants
        device_id = "device-001"
        conv_id = str(uuid4())
        # Create list of unique participants, ensuring device_id is included
        # Start from 2 to avoid duplicate with device_id
        participants = [device_id] + [f"device-{i:03d}" for i in range(2, MAX_GROUP_SIZE + 1)]
        
        self.service.create_conversation(
            device_id=device_id,
            participants=participants,
            conversation_id=conv_id,
        )
        
        # Attempt to join
        new_device = "device-over-limit"
        response = self.service.join_conversation(
            device_id=new_device,
            conversation_id=conv_id,
        )
        
        # Verify error response
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["error_code"], 400)
        self.assertIn("max group size", response["message"])
    
    def test_join_conversation_closed(self) -> None:
        """
        Test join closed conversation per State Machines (#7), Section 4.
        
        Cannot join closed conversations.
        """
        # Create and close conversation
        device_id = "device-001"
        conv_id = str(uuid4())
        self.service.create_conversation(
            device_id=device_id,
            participants=[device_id],
            conversation_id=conv_id,
        )
        
        # Close conversation
        self.service.close_conversation(device_id=device_id, conversation_id=conv_id)
        
        # Attempt to join
        new_device = "device-002"
        response = self.service.join_conversation(
            device_id=new_device,
            conversation_id=conv_id,
        )
        
        # Verify error response
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["error_code"], 404)
        self.assertIn("closed", response["message"])
    
    def test_leave_conversation_success(self) -> None:
        """
        Test leave conversation API per State Machines (#7), Section 4.
        
        Any participant may leave a conversation.
        """
        # Create conversation
        device_id = "device-001"
        conv_id = str(uuid4())
        self.service.create_conversation(
            device_id=device_id,
            participants=[device_id, "device-002", "device-003"],
            conversation_id=conv_id,
        )
        
        # Leave conversation
        response = self.service.leave_conversation(
            device_id=device_id,
            conversation_id=conv_id,
        )
        
        # Verify success response
        self.assertEqual(response["status"], "success")
        
        # Verify participant removed
        participants = self.conversation_registry.get_conversation_participants(conv_id)
        self.assertIsNotNone(participants)
        self.assertNotIn(device_id, participants)
        self.assertEqual(len(participants), 2)
    
    def test_leave_conversation_closes_when_all_leave(self) -> None:
        """
        Test conversation closure when all participants leave per State Machines (#7), Section 4.
        
        Active -> Closed when all participants removed.
        """
        # Create conversation with single participant
        device_id = "device-001"
        conv_id = str(uuid4())
        self.service.create_conversation(
            device_id=device_id,
            participants=[device_id],
            conversation_id=conv_id,
        )
        
        # Leave conversation (last participant)
        response = self.service.leave_conversation(
            device_id=device_id,
            conversation_id=conv_id,
        )
        
        # Verify success response
        self.assertEqual(response["status"], "success")
        self.assertTrue(response.get("conversation_closed", False))
        
        # Verify conversation closed
        self.assertFalse(self.conversation_registry.is_conversation_active(conv_id))
    
    def test_leave_conversation_not_participant(self) -> None:
        """
        Test leave conversation when not a participant.
        
        Returns 404 error.
        """
        # Create conversation
        device_id = "device-001"
        conv_id = str(uuid4())
        self.service.create_conversation(
            device_id=device_id,
            participants=[device_id],
            conversation_id=conv_id,
        )
        
        # Attempt to leave as non-participant
        non_participant = "device-002"
        response = self.service.leave_conversation(
            device_id=non_participant,
            conversation_id=conv_id,
        )
        
        # Verify error response
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["error_code"], 404)
        self.assertIn("Not a participant", response["message"])
    
    def test_close_conversation_success(self) -> None:
        """
        Test close conversation API per State Machines (#7), Section 4.
        
        Only participants may close a conversation.
        Active -> Closed transition.
        """
        # Create conversation
        device_id = "device-001"
        conv_id = str(uuid4())
        self.service.create_conversation(
            device_id=device_id,
            participants=[device_id, "device-002"],
            conversation_id=conv_id,
        )
        
        # Close conversation
        response = self.service.close_conversation(
            device_id=device_id,
            conversation_id=conv_id,
        )
        
        # Verify success response
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["state"], ConversationState.CLOSED.value)
        
        # Verify conversation closed
        self.assertFalse(self.conversation_registry.is_conversation_active(conv_id))
    
    def test_close_conversation_not_participant(self) -> None:
        """
        Test close conversation when not a participant.
        
        Only participants may close a conversation.
        """
        # Create conversation
        device_id = "device-001"
        conv_id = str(uuid4())
        self.service.create_conversation(
            device_id=device_id,
            participants=[device_id],
            conversation_id=conv_id,
        )
        
        # Attempt to close as non-participant
        non_participant = "device-002"
        response = self.service.close_conversation(
            device_id=non_participant,
            conversation_id=conv_id,
        )
        
        # Verify error response
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["error_code"], 403)
        self.assertIn("Not a participant", response["message"])
    
    def test_get_conversation_info_participant(self) -> None:
        """
        Test get conversation info for participant.
        
        Participants may view conversation information.
        """
        # Create conversation
        device_id = "device-001"
        conv_id = str(uuid4())
        self.service.create_conversation(
            device_id=device_id,
            participants=[device_id, "device-002"],
            conversation_id=conv_id,
        )
        
        # Get conversation info
        response = self.service.get_conversation_info(
            device_id=device_id,
            conversation_id=conv_id,
        )
        
        # Verify success response
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["conversation_id"], conv_id)
        self.assertEqual(response["state"], ConversationState.ACTIVE.value)
        self.assertTrue(response["is_participant"])
        self.assertEqual(response["participant_count"], 2)
    
    def test_get_conversation_info_revoked_device(self) -> None:
        """
        Test get conversation info for revoked device per Resolved Clarifications (#38).
        
        Revoked devices can view conversation list (neutral enterprise mode).
        """
        # Create conversation
        device_id = "device-001"
        conv_id = str(uuid4())
        self.service.create_conversation(
            device_id=device_id,
            participants=[device_id],
            conversation_id=conv_id,
        )
        
        # Revoke device
        revoked_device = "device-001"
        self.device_registry.is_device_active = Mock(return_value=False)
        
        # Get conversation info (revoked device was participant)
        response = self.service.get_conversation_info(
            device_id=revoked_device,
            conversation_id=conv_id,
        )
        
        # Verify success response (neutral enterprise mode allows viewing)
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["conversation_id"], conv_id)
    
    def test_get_conversation_info_unauthorized(self) -> None:
        """
        Test get conversation info for unauthorized device.
        
        Non-participants cannot view conversation info (unless revoked).
        """
        # Create conversation
        device_id = "device-001"
        conv_id = str(uuid4())
        self.service.create_conversation(
            device_id=device_id,
            participants=[device_id],
            conversation_id=conv_id,
        )
        
        # Attempt to get info as non-participant
        non_participant = "device-002"
        response = self.service.get_conversation_info(
            device_id=non_participant,
            conversation_id=conv_id,
        )
        
        # Verify error response
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["error_code"], 403)
        self.assertIn("Not authorized", response["message"])


if __name__ == "__main__":
    unittest.main()
