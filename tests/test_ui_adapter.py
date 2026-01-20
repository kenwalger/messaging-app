"""
Unit tests for UI domain adapter layer.

References:
- UX Behavior (#12)
- Copy Rules (#13)
- Functional Specification (#6)
- Client-Facing API Boundary (latest)
"""

import unittest
from datetime import datetime, timedelta
from uuid import uuid4

from src.client.ui_adapter import UIAdapter
from src.shared.client_types import (
    ClientConversationDTO,
    ClientConversationState,
    ClientMessageDTO,
    ClientMessageState,
)
from src.shared.constants import DEFAULT_MESSAGE_EXPIRATION_DAYS
from src.shared.message_types import utc_now


class TestUIAdapter(unittest.TestCase):
    """Test cases for UIAdapter per UX Behavior (#12) and Copy Rules (#13)."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.adapter = UIAdapter()
    
    def test_map_message_to_view_model_derives_expiration(self) -> None:
        """
        Test message view model derives expiration flag per UX Behavior (#12), Section 3.4.
        
        Expired messages are deterministically derived from expires_at < current_time.
        """
        past_time = utc_now() - timedelta(days=1)
        future_time = utc_now() + timedelta(days=DEFAULT_MESSAGE_EXPIRATION_DAYS)
        
        # Expired message
        expired_dto = ClientMessageDTO(
            message_id=str(uuid4()),
            sender_id="device-001",
            conversation_id="conv-001",
            state=ClientMessageState.EXPIRED,
            created_at=past_time,
            expires_at=past_time,
        )
        
        view_model = self.adapter.map_message_to_view_model(expired_dto)
        self.assertTrue(view_model.is_expired)
        
        # Unexpired message
        unexpired_dto = ClientMessageDTO(
            message_id=str(uuid4()),
            sender_id="device-001",
            conversation_id="conv-001",
            state=ClientMessageState.DELIVERED,
            created_at=utc_now(),
            expires_at=future_time,
        )
        
        view_model = self.adapter.map_message_to_view_model(unexpired_dto)
        self.assertFalse(view_model.is_expired)
    
    def test_map_message_to_view_model_derives_failure(self) -> None:
        """
        Test message view model derives failure flag per UX Behavior (#12), Section 3.6.
        
        Failed messages are explicitly distinguishable.
        """
        failed_dto = ClientMessageDTO(
            message_id=str(uuid4()),
            sender_id="device-001",
            conversation_id="conv-001",
            state=ClientMessageState.FAILED,
            created_at=utc_now(),
            expires_at=utc_now() + timedelta(days=7),
        )
        
        view_model = self.adapter.map_message_to_view_model(failed_dto)
        self.assertTrue(view_model.is_failed)
        self.assertEqual(view_model.display_state, "failed")
        
        # Non-failed message
        delivered_dto = ClientMessageDTO(
            message_id=str(uuid4()),
            sender_id="device-001",
            conversation_id="conv-001",
            state=ClientMessageState.DELIVERED,
            created_at=utc_now(),
            expires_at=utc_now() + timedelta(days=7),
        )
        
        view_model = self.adapter.map_message_to_view_model(delivered_dto)
        self.assertFalse(view_model.is_failed)
        self.assertEqual(view_model.display_state, "delivered")
    
    def test_map_message_to_view_model_read_only_mode(self) -> None:
        """
        Test message view model handles read-only mode per Resolved Clarifications (#38).
        
        Neutral enterprise mode maps to is_read_only = true.
        """
        dto = ClientMessageDTO(
            message_id=str(uuid4()),
            sender_id="device-001",
            conversation_id="conv-001",
            state=ClientMessageState.DELIVERED,
            created_at=utc_now(),
            expires_at=utc_now() + timedelta(days=7),
        )
        
        # Read-only mode
        view_model = self.adapter.map_message_to_view_model(dto, is_read_only=True)
        self.assertTrue(view_model.is_read_only)
        
        # Active mode
        view_model = self.adapter.map_message_to_view_model(dto, is_read_only=False)
        self.assertFalse(view_model.is_read_only)
    
    def test_map_conversation_to_view_model_derives_can_send(self) -> None:
        """
        Test conversation view model derives can_send flag per Resolved Clarifications (#38).
        
        can_send is true if not read-only and conversation is active.
        """
        active_dto = ClientConversationDTO(
            conversation_id=str(uuid4()),
            state=ClientConversationState.ACTIVE,
            participant_count=2,
            created_at=utc_now(),
        )
        
        # Active conversation, not read-only
        view_model = self.adapter.map_conversation_to_view_model(active_dto, is_read_only=False)
        self.assertTrue(view_model.can_send)
        self.assertFalse(view_model.send_disabled)
        
        # Active conversation, read-only
        view_model = self.adapter.map_conversation_to_view_model(active_dto, is_read_only=True)
        self.assertFalse(view_model.can_send)
        self.assertTrue(view_model.send_disabled)
        
        # Closed conversation, not read-only
        closed_dto = ClientConversationDTO(
            conversation_id=str(uuid4()),
            state=ClientConversationState.CLOSED,
            participant_count=2,
            created_at=utc_now(),
        )
        
        view_model = self.adapter.map_conversation_to_view_model(closed_dto, is_read_only=False)
        self.assertFalse(view_model.can_send)
        self.assertTrue(view_model.send_disabled)
    
    def test_map_conversation_to_view_model_read_only_mode(self) -> None:
        """
        Test conversation view model handles read-only mode per Resolved Clarifications (#38).
        
        Neutral enterprise mode maps to is_read_only = true, send_disabled = true.
        """
        dto = ClientConversationDTO(
            conversation_id=str(uuid4()),
            state=ClientConversationState.ACTIVE,
            participant_count=2,
            created_at=utc_now(),
        )
        
        # Read-only mode
        view_model = self.adapter.map_conversation_to_view_model(dto, is_read_only=True)
        self.assertTrue(view_model.is_read_only)
        self.assertTrue(view_model.send_disabled)
        self.assertFalse(view_model.can_send)
        
        # Active mode
        view_model = self.adapter.map_conversation_to_view_model(dto, is_read_only=False)
        self.assertFalse(view_model.is_read_only)
        self.assertFalse(view_model.send_disabled)
        self.assertTrue(view_model.can_send)
    
    def test_map_device_state_to_view_model_read_only_mode(self) -> None:
        """
        Test device state view model handles read-only mode per Resolved Clarifications (#38).
        
        Revoked devices can read but cannot send/create/join.
        """
        # Read-only mode (revoked device)
        view_model = self.adapter.map_device_state_to_view_model("device-001", is_read_only=True)
        self.assertTrue(view_model.is_read_only)
        self.assertFalse(view_model.can_send)
        self.assertFalse(view_model.can_create_conversations)
        self.assertFalse(view_model.can_join_conversations)
        self.assertEqual(view_model.display_status, "Messaging Disabled")
        
        # Active mode
        view_model = self.adapter.map_device_state_to_view_model("device-001", is_read_only=False)
        self.assertFalse(view_model.is_read_only)
        self.assertTrue(view_model.can_send)
        self.assertTrue(view_model.can_create_conversations)
        self.assertTrue(view_model.can_join_conversations)
        self.assertEqual(view_model.display_status, "Active Messaging")
    
    def test_sort_messages_reverse_chronological(self) -> None:
        """
        Test message sorting in reverse chronological order per Resolved Clarifications (#53).
        
        Newest first: messages sorted by created_at descending.
        """
        now = utc_now()
        messages = [
            self.adapter.map_message_to_view_model(
                ClientMessageDTO(
                    message_id=str(uuid4()),
                    sender_id="device-001",
                    conversation_id="conv-001",
                    state=ClientMessageState.DELIVERED,
                    created_at=now - timedelta(hours=2),
                    expires_at=now + timedelta(days=7),
                )
            ),
            self.adapter.map_message_to_view_model(
                ClientMessageDTO(
                    message_id=str(uuid4()),
                    sender_id="device-001",
                    conversation_id="conv-001",
                    state=ClientMessageState.DELIVERED,
                    created_at=now,
                    expires_at=now + timedelta(days=7),
                )
            ),
            self.adapter.map_message_to_view_model(
                ClientMessageDTO(
                    message_id=str(uuid4()),
                    sender_id="device-001",
                    conversation_id="conv-001",
                    state=ClientMessageState.DELIVERED,
                    created_at=now - timedelta(hours=1),
                    expires_at=now + timedelta(days=7),
                )
            ),
        ]
        
        sorted_messages = self.adapter.sort_messages_reverse_chronological(messages)
        
        # Verify newest first
        self.assertEqual(sorted_messages[0].created_at, now)
        self.assertEqual(sorted_messages[1].created_at, now - timedelta(hours=1))
        self.assertEqual(sorted_messages[2].created_at, now - timedelta(hours=2))
    
    def test_sort_conversations_reverse_chronological(self) -> None:
        """
        Test conversation sorting in reverse chronological order per Resolved Clarifications (#53).
        
        Newest first: conversations sorted by sort_key (last_message_at or created_at) descending.
        """
        now = utc_now()
        conversations = [
            self.adapter.map_conversation_to_view_model(
                ClientConversationDTO(
                    conversation_id=str(uuid4()),
                    state=ClientConversationState.ACTIVE,
                    participant_count=2,
                    created_at=now - timedelta(hours=2),
                    last_message_at=now - timedelta(hours=1),
                )
            ),
            self.adapter.map_conversation_to_view_model(
                ClientConversationDTO(
                    conversation_id=str(uuid4()),
                    state=ClientConversationState.ACTIVE,
                    participant_count=2,
                    created_at=now,
                    last_message_at=now,
                )
            ),
            self.adapter.map_conversation_to_view_model(
                ClientConversationDTO(
                    conversation_id=str(uuid4()),
                    state=ClientConversationState.ACTIVE,
                    participant_count=2,
                    created_at=now - timedelta(hours=1),
                    last_message_at=None,  # Uses created_at as sort_key
                )
            ),
        ]
        
        sorted_conversations = self.adapter.sort_conversations_reverse_chronological(conversations)
        
        # Verify newest first (by last_message_at or created_at)
        self.assertEqual(sorted_conversations[0].last_message_at, now)
        self.assertEqual(sorted_conversations[1].last_message_at, now - timedelta(hours=1))
        self.assertIsNone(sorted_conversations[2].last_message_at)
    
    def test_filter_expired_messages(self) -> None:
        """
        Test expired message filtering per UX Behavior (#12), Section 3.4.
        
        Expired messages are removed automatically; no undo.
        """
        now = utc_now()
        messages = [
            self.adapter.map_message_to_view_model(
                ClientMessageDTO(
                    message_id=str(uuid4()),
                    sender_id="device-001",
                    conversation_id="conv-001",
                    state=ClientMessageState.EXPIRED,
                    created_at=now - timedelta(days=2),
                    expires_at=now - timedelta(days=1),
                )
            ),
            self.adapter.map_message_to_view_model(
                ClientMessageDTO(
                    message_id=str(uuid4()),
                    sender_id="device-001",
                    conversation_id="conv-001",
                    state=ClientMessageState.DELIVERED,
                    created_at=now,
                    expires_at=now + timedelta(days=7),
                )
            ),
        ]
        
        filtered = self.adapter.filter_expired_messages(messages)
        
        # Only non-expired message remains
        self.assertEqual(len(filtered), 1)
        self.assertFalse(filtered[0].is_expired)
    
    def test_filter_failed_messages(self) -> None:
        """
        Test failed message filtering per UX Behavior (#12), Section 3.6.
        
        Failed messages are explicitly distinguishable.
        """
        messages = [
            self.adapter.map_message_to_view_model(
                ClientMessageDTO(
                    message_id=str(uuid4()),
                    sender_id="device-001",
                    conversation_id="conv-001",
                    state=ClientMessageState.FAILED,
                    created_at=utc_now(),
                    expires_at=utc_now() + timedelta(days=7),
                )
            ),
            self.adapter.map_message_to_view_model(
                ClientMessageDTO(
                    message_id=str(uuid4()),
                    sender_id="device-001",
                    conversation_id="conv-001",
                    state=ClientMessageState.DELIVERED,
                    created_at=utc_now(),
                    expires_at=utc_now() + timedelta(days=7),
                )
            ),
        ]
        
        filtered = self.adapter.filter_failed_messages(messages)
        
        # Only failed message remains
        self.assertEqual(len(filtered), 1)
        self.assertTrue(filtered[0].is_failed)
    
    def test_filter_active_conversations(self) -> None:
        """
        Test active conversation filtering per UX Behavior (#12), Section 3.2.
        
        Display active conversations only.
        """
        conversations = [
            self.adapter.map_conversation_to_view_model(
                ClientConversationDTO(
                    conversation_id=str(uuid4()),
                    state=ClientConversationState.ACTIVE,
                    participant_count=2,
                    created_at=utc_now(),
                )
            ),
            self.adapter.map_conversation_to_view_model(
                ClientConversationDTO(
                    conversation_id=str(uuid4()),
                    state=ClientConversationState.CLOSED,
                    participant_count=2,
                    created_at=utc_now(),
                )
            ),
        ]
        
        filtered = self.adapter.filter_active_conversations(conversations)
        
        # Only active conversation remains
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].state, ClientConversationState.ACTIVE)
    
    def test_message_view_model_display_state(self) -> None:
        """
        Test message view model display state per Copy Rules (#13), Section 3.
        
        Display states are deterministic and neutral.
        """
        now = utc_now()
        
        # Expired message
        expired = self.adapter.map_message_to_view_model(
            ClientMessageDTO(
                message_id=str(uuid4()),
                sender_id="device-001",
                conversation_id="conv-001",
                state=ClientMessageState.EXPIRED,
                created_at=now - timedelta(days=2),
                expires_at=now - timedelta(days=1),
            )
        )
        self.assertEqual(expired.display_state, "expired")
        
        # Failed message
        failed = self.adapter.map_message_to_view_model(
            ClientMessageDTO(
                message_id=str(uuid4()),
                sender_id="device-001",
                conversation_id="conv-001",
                state=ClientMessageState.FAILED,
                created_at=now,
                expires_at=now + timedelta(days=7),
            )
        )
        self.assertEqual(failed.display_state, "failed")
        
        # Queued message
        queued = self.adapter.map_message_to_view_model(
            ClientMessageDTO(
                message_id=str(uuid4()),
                sender_id="device-001",
                conversation_id="conv-001",
                state=ClientMessageState.SENT,
                created_at=now,
                expires_at=now + timedelta(days=7),
            )
        )
        self.assertEqual(queued.display_state, "queued")
        
        # Delivered message
        delivered = self.adapter.map_message_to_view_model(
            ClientMessageDTO(
                message_id=str(uuid4()),
                sender_id="device-001",
                conversation_id="conv-001",
                state=ClientMessageState.DELIVERED,
                created_at=now,
                expires_at=now + timedelta(days=7),
            )
        )
        self.assertEqual(delivered.display_state, "delivered")
    
    def test_conversation_view_model_display_name(self) -> None:
        """
        Test conversation view model display name per Copy Rules (#13), Section 3.
        
        Display names are deterministic and neutral.
        """
        # Single participant
        single = self.adapter.map_conversation_to_view_model(
            ClientConversationDTO(
                conversation_id=str(uuid4()),
                state=ClientConversationState.ACTIVE,
                participant_count=1,
                created_at=utc_now(),
            )
        )
        self.assertEqual(single.display_name, "Conversation")
        
        # Multiple participants
        multi = self.adapter.map_conversation_to_view_model(
            ClientConversationDTO(
                conversation_id=str(uuid4()),
                state=ClientConversationState.ACTIVE,
                participant_count=3,
                created_at=utc_now(),
            )
        )
        self.assertEqual(multi.display_name, "Conversation (3 participants)")


if __name__ == "__main__":
    unittest.main()
