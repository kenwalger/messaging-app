"""
Unit tests for conversation management module.

References:
- Functional Specification (#6), Section 4.1
- State Machines (#7), Section 4
- Data Classification & Retention (#8)
- UX Behavior (#12), Section 3.2
- Resolved Specs & Clarifications
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

from src.client.conversation_manager import ConversationManager
from src.shared.constants import MAX_GROUP_SIZE
from src.shared.conversation_types import Conversation, ConversationState
from src.shared.message_types import utc_now


class TestConversationManager(unittest.TestCase):
    """Test cases for ConversationManager per Functional Spec (#6) and State Machines (#7)."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.device_id = "test-device-001"
        self.device_registry = Mock()
        self.device_registry.is_device_active = Mock(return_value=True)
        self.log_service = Mock()
        
        self.manager = ConversationManager(
            device_id=self.device_id,
            device_registry=self.device_registry,
            log_service=self.log_service,
            device_revoked=False,
        )
    
    def test_create_conversation_success(self) -> None:
        """
        Test conversation creation per Functional Spec (#6), Section 4.1.
        
        Conversation should be created in Active state with explicitly defined participants.
        """
        participants = [self.device_id, "participant-001", "participant-002"]
        
        conversation = self.manager.create_conversation(participants=participants)
        
        # Verify conversation structure per Functional Spec (#6), Section 4.1
        self.assertIsNotNone(conversation.conversation_id)
        self.assertEqual(conversation.state, ConversationState.ACTIVE)
        self.assertEqual(len(conversation.participants), 3)
        self.assertIn(self.device_id, conversation.participants)
        self.assertEqual(conversation.created_by, self.device_id)
    
    def test_create_conversation_max_group_size(self) -> None:
        """
        Test conversation creation with max group size per Resolved TBDs.
        
        Max 50 participants per conversation.
        """
        # Should succeed with max group size
        participants = [f"participant-{i:03d}" for i in range(MAX_GROUP_SIZE)]
        participants[0] = self.device_id  # Replace first with device_id
        
        conversation = self.manager.create_conversation(participants=participants)
        self.assertEqual(len(conversation.participants), MAX_GROUP_SIZE)
        
        # Should fail with group size > 50
        participants_over_limit = [f"participant-{i:03d}" for i in range(MAX_GROUP_SIZE + 1)]
        participants_over_limit[0] = self.device_id
        
        with self.assertRaises(ValueError):
            self.manager.create_conversation(participants=participants_over_limit)
    
    def test_create_conversation_device_revoked(self) -> None:
        """
        Test conversation creation with revoked device per Resolved Clarifications.
        
        Revoked devices cannot create new conversations (neutral enterprise mode).
        """
        revoked_manager = ConversationManager(
            device_id=self.device_id,
            device_revoked=True,
        )
        
        participants = [self.device_id, "participant-001"]
        
        with self.assertRaises(RuntimeError):
            revoked_manager.create_conversation(participants=participants)
    
    def test_create_conversation_auto_includes_device(self) -> None:
        """
        Test that device_id is automatically included in participants.
        
        Per Functional Spec (#6), device creating conversation should be included.
        """
        participants = ["participant-001", "participant-002"]
        
        conversation = self.manager.create_conversation(participants=participants)
        
        # Device should be included automatically
        self.assertIn(self.device_id, conversation.participants)
        self.assertEqual(len(conversation.participants), 3)
    
    def test_add_participant_success(self) -> None:
        """
        Test participant addition per State Machines (#7), Section 4.
        
        Participant should be added to Active conversation.
        """
        participants = [self.device_id, "participant-001"]
        conversation = self.manager.create_conversation(participants=participants)
        
        # Add participant
        success = self.manager.add_participant(conversation.conversation_id, "participant-002")
        
        self.assertTrue(success)
        updated = self.manager.get_conversation(conversation.conversation_id)
        self.assertIsNotNone(updated)
        self.assertEqual(len(updated.participants), 3)
        self.assertIn("participant-002", updated.participants)
    
    def test_add_participant_max_group_size(self) -> None:
        """
        Test participant addition with max group size per Resolved TBDs.
        
        Cannot add participant if group size limit reached.
        """
        # Create conversation with max participants
        participants = [f"participant-{i:03d}" for i in range(MAX_GROUP_SIZE)]
        participants[0] = self.device_id
        conversation = self.manager.create_conversation(participants=participants)
        
        # Should fail to add another participant
        success = self.manager.add_participant(conversation.conversation_id, "participant-over-limit")
        
        self.assertFalse(success)
        updated = self.manager.get_conversation(conversation.conversation_id)
        self.assertIsNotNone(updated)
        self.assertEqual(len(updated.participants), MAX_GROUP_SIZE)
    
    def test_add_participant_closed_conversation(self) -> None:
        """
        Test participant addition to closed conversation per State Machines (#7), Section 4.
        
        Cannot add participants to closed conversations.
        """
        participants = [self.device_id, "participant-001"]
        conversation = self.manager.create_conversation(participants=participants)
        
        # Close conversation
        self.manager.close_conversation(conversation.conversation_id)
        
        # Should fail to add participant
        success = self.manager.add_participant(conversation.conversation_id, "participant-002")
        
        self.assertFalse(success)
    
    def test_remove_participant_success(self) -> None:
        """
        Test participant removal per State Machines (#7), Section 4.
        
        Participant should be removed from conversation.
        """
        participants = [self.device_id, "participant-001", "participant-002"]
        conversation = self.manager.create_conversation(participants=participants)
        
        # Remove participant
        success = self.manager.remove_participant(conversation.conversation_id, "participant-001")
        
        self.assertTrue(success)
        updated = self.manager.get_conversation(conversation.conversation_id)
        self.assertIsNotNone(updated)
        self.assertEqual(len(updated.participants), 2)
        self.assertNotIn("participant-001", updated.participants)
        self.assertEqual(updated.state, ConversationState.ACTIVE)  # Still active
    
    def test_remove_participant_closes_conversation(self) -> None:
        """
        Test conversation closure when all participants removed per State Machines (#7), Section 4.
        
        Active -> Closed when all participants removed.
        """
        participants = [self.device_id, "participant-001"]
        conversation = self.manager.create_conversation(participants=participants)
        
        # Remove other participant
        self.manager.remove_participant(conversation.conversation_id, "participant-001")
        
        # Remove device (last participant)
        self.manager.remove_participant(conversation.conversation_id, self.device_id)
        
        updated = self.manager.get_conversation(conversation.conversation_id)
        self.assertIsNotNone(updated)
        self.assertEqual(updated.state, ConversationState.CLOSED)
        self.assertEqual(len(updated.participants), 0)
    
    def test_close_conversation_success(self) -> None:
        """
        Test conversation closure per State Machines (#7), Section 4.
        
        Active -> Closed transition.
        """
        participants = [self.device_id, "participant-001"]
        conversation = self.manager.create_conversation(participants=participants)
        
        # Close conversation
        success = self.manager.close_conversation(conversation.conversation_id)
        
        self.assertTrue(success)
        updated = self.manager.get_conversation(conversation.conversation_id)
        self.assertIsNotNone(updated)
        self.assertEqual(updated.state, ConversationState.CLOSED)
    
    def test_close_conversation_device_revoked(self) -> None:
        """
        Test conversation closure with revoked device per Resolved Clarifications.
        
        Revoked devices cannot modify conversations.
        """
        participants = [self.device_id, "participant-001"]
        conversation = self.manager.create_conversation(participants=participants)
        
        # Revoke device
        self.manager.handle_device_revocation()
        
        # Should fail to close conversation
        with self.assertRaises(RuntimeError):
            self.manager.close_conversation(conversation.conversation_id)
    
    def test_can_send_to_conversation_active(self) -> None:
        """
        Test message sending permission for active conversation per Resolved Clarifications.
        
        Active conversations accept new messages.
        """
        participants = [self.device_id, "participant-001"]
        conversation = self.manager.create_conversation(participants=participants)
        
        can_send = self.manager.can_send_to_conversation(conversation.conversation_id)
        
        self.assertTrue(can_send)
    
    def test_can_send_to_conversation_closed(self) -> None:
        """
        Test message sending permission for closed conversation per Resolved Clarifications.
        
        Closed conversations do not accept new messages.
        """
        participants = [self.device_id, "participant-001"]
        conversation = self.manager.create_conversation(participants=participants)
        
        # Close conversation
        self.manager.close_conversation(conversation.conversation_id)
        
        can_send = self.manager.can_send_to_conversation(conversation.conversation_id)
        
        self.assertFalse(can_send)
    
    def test_can_send_to_conversation_device_revoked(self) -> None:
        """
        Test message sending permission with revoked device per Resolved Clarifications.
        
        Revoked devices cannot send messages.
        """
        participants = [self.device_id, "participant-001"]
        conversation = self.manager.create_conversation(participants=participants)
        
        # Revoke device
        self.manager.handle_device_revocation()
        
        can_send = self.manager.can_send_to_conversation(conversation.conversation_id)
        
        self.assertFalse(can_send)
    
    def test_get_active_conversations(self) -> None:
        """
        Test getting active conversations per UX Behavior (#12), Section 3.2.
        
        Should return only active conversations, sorted by last message timestamp.
        """
        # Create multiple conversations
        conv1 = self.manager.create_conversation(participants=[self.device_id, "p1"])
        conv2 = self.manager.create_conversation(participants=[self.device_id, "p2"])
        conv3 = self.manager.create_conversation(participants=[self.device_id, "p3"])
        
        # Update last message timestamps
        self.manager.update_conversation_last_message(conv1.conversation_id, utc_now() - timedelta(hours=1))
        self.manager.update_conversation_last_message(conv2.conversation_id, utc_now())
        self.manager.update_conversation_last_message(conv3.conversation_id, utc_now() - timedelta(hours=2))
        
        # Close one conversation
        self.manager.close_conversation(conv3.conversation_id)
        
        # Get active conversations
        active = self.manager.get_active_conversations()
        
        # Should return only active conversations (conv1, conv2)
        self.assertEqual(len(active), 2)
        
        # Should be sorted by last message timestamp (most recent first)
        self.assertEqual(active[0].conversation_id, conv2.conversation_id)
        self.assertEqual(active[1].conversation_id, conv1.conversation_id)
    
    def test_handle_participant_revocation(self) -> None:
        """
        Test participant revocation handling per State Machines (#7), Section 4.
        
        Revoked participant should be removed from all conversations.
        """
        # Create conversations with shared participant
        participant_to_revoke = "participant-to-revoke"
        conv1 = self.manager.create_conversation(participants=[self.device_id, participant_to_revoke, "p1"])
        conv2 = self.manager.create_conversation(participants=[self.device_id, participant_to_revoke, "p2"])
        
        # Revoke participant
        affected = self.manager.handle_participant_revocation(participant_to_revoke)
        
        # Both conversations should be affected
        self.assertEqual(len(affected), 2)
        self.assertIn(conv1.conversation_id, affected)
        self.assertIn(conv2.conversation_id, affected)
        
        # Participant should be removed from both
        updated1 = self.manager.get_conversation(conv1.conversation_id)
        updated2 = self.manager.get_conversation(conv2.conversation_id)
        self.assertIsNotNone(updated1)
        self.assertIsNotNone(updated2)
        self.assertNotIn(participant_to_revoke, updated1.participants)
        self.assertNotIn(participant_to_revoke, updated2.participants)
    
    def test_cleanup_closed_conversations(self) -> None:
        """
        Test cleanup of closed conversations per Data Classification (#8), Section 4.
        
        Closed conversations should be removed from storage.
        """
        # Create and close conversations
        conv1 = self.manager.create_conversation(participants=[self.device_id, "p1"])
        conv2 = self.manager.create_conversation(participants=[self.device_id, "p2"])
        conv3 = self.manager.create_conversation(participants=[self.device_id, "p3"])
        
        # Close two conversations
        self.manager.close_conversation(conv1.conversation_id)
        self.manager.close_conversation(conv2.conversation_id)
        
        # Cleanup closed conversations
        removed_count = self.manager.cleanup_closed_conversations()
        
        # Should remove 2 closed conversations
        self.assertEqual(removed_count, 2)
        
        # Closed conversations should be gone
        self.assertIsNone(self.manager.get_conversation(conv1.conversation_id))
        self.assertIsNone(self.manager.get_conversation(conv2.conversation_id))
        
        # Active conversation should remain
        self.assertIsNotNone(self.manager.get_conversation(conv3.conversation_id))
    
    def test_update_last_message_timestamp(self) -> None:
        """
        Test updating last message timestamp per UX Behavior (#12), Section 3.2.
        
        Timestamp should be updated for UI display.
        """
        conversation = self.manager.create_conversation(participants=[self.device_id, "p1"])
        
        timestamp = utc_now()
        success = self.manager.update_conversation_last_message(conversation.conversation_id, timestamp)
        
        self.assertTrue(success)
        updated = self.manager.get_conversation(conversation.conversation_id)
        self.assertIsNotNone(updated)
        self.assertEqual(updated.last_message_timestamp, timestamp)


if __name__ == "__main__":
    unittest.main()
