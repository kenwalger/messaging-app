"""
Unit tests for API adapter layer.

References:
- API Contracts (#10)
- UX Behavior (#12)
- Copy Rules (#13)
- Functional Specification (#6)
"""

import unittest
from datetime import datetime, timedelta
from uuid import uuid4

from src.backend.api_adapter import APIAdapter
from src.shared.client_types import (
    ClientConversationState,
    ClientErrorCode,
    ClientErrorResponse,
    ClientMessageState,
)
from src.shared.constants import (
    DEFAULT_MESSAGE_EXPIRATION_DAYS,
    ERROR_MESSAGING_DISABLED,
)
from src.shared.conversation_types import Conversation, ConversationState
from src.shared.device_identity_types import DeviceIdentityState
from src.shared.message_types import Message, MessageState, utc_now


class TestAPIAdapter(unittest.TestCase):
    """Test cases for APIAdapter per API Contracts (#10) and UX Behavior (#12)."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.adapter = APIAdapter()
    
    def test_map_message_state_pending_delivery_to_sent(self) -> None:
        """
        Test message state mapping per UX Behavior (#12), Section 4.
        
        PendingDelivery (internal) maps to SENT (client-visible).
        """
        state = self.adapter._map_message_state(MessageState.PENDING_DELIVERY)
        self.assertEqual(state, ClientMessageState.SENT)
    
    def test_map_message_state_delivered_to_delivered(self) -> None:
        """
        Test message state mapping per UX Behavior (#12), Section 4.
        
        Delivered (internal) maps to DELIVERED (client-visible).
        """
        state = self.adapter._map_message_state(MessageState.DELIVERED)
        self.assertEqual(state, ClientMessageState.DELIVERED)
    
    def test_map_message_state_failed_to_failed(self) -> None:
        """
        Test message state mapping per UX Behavior (#12), Section 4.
        
        Failed (internal) maps to FAILED (client-visible).
        """
        state = self.adapter._map_message_state(MessageState.FAILED)
        self.assertEqual(state, ClientMessageState.FAILED)
    
    def test_map_message_state_expired_to_expired(self) -> None:
        """
        Test message state mapping per UX Behavior (#12), Section 4.
        
        Expired (internal) maps to EXPIRED (client-visible).
        """
        state = self.adapter._map_message_state(MessageState.EXPIRED)
        self.assertEqual(state, ClientMessageState.EXPIRED)
    
    def test_map_message_to_dto_hides_internal_details(self) -> None:
        """
        Test message DTO hides internal details per UX Behavior (#12), Section 3.6.
        
        Clients never see: retry_count, internal state names, cryptographic material.
        """
        message = Message(
            message_id=uuid4(),
            sender_id="device-001",
            recipients=["device-002"],
            payload=b"encrypted-payload",
            conversation_id="conv-001",
            creation_timestamp=utc_now(),
            expiration_timestamp=utc_now() + timedelta(days=DEFAULT_MESSAGE_EXPIRATION_DAYS),
            state=MessageState.PENDING_DELIVERY,
            retry_count=3,  # Internal detail, should not appear in DTO
        )
        
        dto = self.adapter.map_message_to_dto(message)
        
        # Verify client-visible fields
        self.assertEqual(dto.message_id, str(message.message_id))
        self.assertEqual(dto.sender_id, message.sender_id)
        self.assertEqual(dto.state, ClientMessageState.SENT)  # Mapped from PENDING_DELIVERY
        
        # Verify internal details are hidden (no retry_count in DTO)
        self.assertFalse(hasattr(dto, "retry_count"))
        self.assertFalse(hasattr(dto, "payload"))  # No payload in DTO
    
    def test_map_conversation_to_dto_hides_internal_details(self) -> None:
        """
        Test conversation DTO hides internal details per UX Behavior (#12), Section 3.2.
        
        Clients see participant_count, not individual participant IDs.
        """
        conversation = Conversation(
            conversation_id=str(uuid4()),
            participants=["device-001", "device-002", "device-003"],
            state=ConversationState.ACTIVE,
            created_at=utc_now(),
        )
        
        dto = self.adapter.map_conversation_to_dto(conversation)
        
        # Verify client-visible fields
        self.assertEqual(dto.conversation_id, str(conversation.conversation_id))
        self.assertEqual(dto.state, ClientConversationState.ACTIVE)
        self.assertEqual(dto.participant_count, 3)
        
        # Verify internal details are hidden (no participant list in DTO)
        self.assertFalse(hasattr(dto, "participants"))
    
    def test_create_error_response_uses_standard_messages(self) -> None:
        """
        Test error response uses standard messages per Copy Rules (#13), Section 4.
        
        Error messages are deterministic and neutral.
        """
        error_response = self.adapter.create_error_response(ClientErrorCode.REVOKED_DEVICE)
        
        self.assertEqual(error_response.error_code, ClientErrorCode.REVOKED_DEVICE)
        self.assertEqual(error_response.message, ERROR_MESSAGING_DISABLED)
        self.assertEqual(error_response.api_version, "v1")
    
    def test_create_error_response_no_sensitive_info(self) -> None:
        """
        Test error response contains no sensitive information per Copy Rules (#13), Section 4.
        
        No technical details, stack traces, or sensitive data exposed.
        """
        error_response = self.adapter.create_error_response(ClientErrorCode.BACKEND_FAILURE)
        
        error_dict = error_response.to_dict()
        
        # Verify no sensitive fields
        self.assertNotIn("stack_trace", error_dict)
        self.assertNotIn("internal_error", error_dict)
        self.assertNotIn("technical_details", error_dict)
        
        # Verify only safe fields present
        self.assertIn("error_code", error_dict)
        self.assertIn("message", error_dict)
        self.assertIn("api_version", error_dict)
        self.assertIn("timestamp", error_dict)
    
    def test_normalize_backend_error_hides_internal_details(self) -> None:
        """
        Test backend error normalization per Copy Rules (#13), Section 4.
        
        Clients never see internal error stacks or technical details.
        """
        # Create an internal exception with technical details
        internal_error = ValueError("Internal technical error: retry_count exceeded")
        
        error_response = self.adapter.normalize_backend_error(internal_error)
        
        # Verify error response is neutral
        self.assertIsInstance(error_response, ClientErrorResponse)
        self.assertNotIn("retry_count", error_response.message)
        self.assertNotIn("technical", error_response.message.lower())
        self.assertEqual(error_response.api_version, "v1")
    
    def test_create_success_response_includes_version(self) -> None:
        """
        Test success response includes API version per API Contracts (#10).
        
        All responses are versioned (v1).
        """
        response = self.adapter.create_success_response(data={"test": "data"})
        
        self.assertEqual(response.status, "success")
        self.assertEqual(response.api_version, "v1")
        self.assertIsNotNone(response.data)
    
    def test_create_message_list_response(self) -> None:
        """
        Test message list response per API Contracts (#10), Section 3.4.
        
        Response includes messages array and API version.
        """
        messages = [
            Message(
                message_id=uuid4(),
                sender_id="device-001",
                recipients=["device-002"],
                payload=b"encrypted-1",
                conversation_id="conv-001",
                creation_timestamp=utc_now(),
                expiration_timestamp=utc_now() + timedelta(days=7),
                state=MessageState.DELIVERED,
            ),
            Message(
                message_id=uuid4(),
                sender_id="device-002",
                recipients=["device-001"],
                payload=b"encrypted-2",
                conversation_id="conv-001",
                creation_timestamp=utc_now(),
                expiration_timestamp=utc_now() + timedelta(days=7),
                state=MessageState.PENDING_DELIVERY,
            ),
        ]
        
        response = self.adapter.create_message_list_response(messages)
        
        self.assertEqual(response["api_version"], "v1")
        self.assertEqual(len(response["messages"]), 2)
        self.assertEqual(response["messages"][0]["state"], "delivered")
        self.assertEqual(response["messages"][1]["state"], "sent")  # Mapped from PENDING_DELIVERY
    
    def test_create_conversation_list_response(self) -> None:
        """
        Test conversation list response per UX Behavior (#12), Section 3.2.
        
        Response includes conversations array and API version.
        """
        conversations = [
            Conversation(
                conversation_id=str(uuid4()),
                participants=["device-001", "device-002"],
                state=ConversationState.ACTIVE,
                created_at=utc_now(),
            ),
            Conversation(
                conversation_id=str(uuid4()),
                participants=["device-001"],
                state=ConversationState.CLOSED,
                created_at=utc_now(),
            ),
        ]
        
        response = self.adapter.create_conversation_list_response(conversations)
        
        self.assertEqual(response["api_version"], "v1")
        self.assertEqual(len(response["conversations"]), 2)
        self.assertEqual(response["conversations"][0]["state"], "active")
        self.assertEqual(response["conversations"][1]["state"], "closed")
    
    def test_map_device_state_to_read_only(self) -> None:
        """
        Test device state to read-only mapping per Resolved Clarifications (#38).
        
        Revoked devices are in read-only mode (neutral enterprise mode).
        """
        # Revoked device should be read-only
        is_read_only = self.adapter.map_device_state_to_read_only(DeviceIdentityState.REVOKED)
        self.assertTrue(is_read_only)
        
        # Active device should not be read-only
        is_read_only = self.adapter.map_device_state_to_read_only(DeviceIdentityState.ACTIVE)
        self.assertFalse(is_read_only)
    
    def test_all_message_states_mapped(self) -> None:
        """
        Test all internal message states are mapped to client-visible states.
        
        No internal state should be unmapped.
        """
        all_internal_states = [
            MessageState.CREATED,
            MessageState.PENDING_DELIVERY,
            MessageState.DELIVERED,
            MessageState.FAILED,
            MessageState.ACTIVE,
            MessageState.EXPIRED,
        ]
        
        for internal_state in all_internal_states:
            client_state = self.adapter._map_message_state(internal_state)
            self.assertIsInstance(client_state, ClientMessageState)
    
    def test_all_conversation_states_mapped(self) -> None:
        """
        Test all internal conversation states are mapped to client-visible states.
        
        No internal state should be unmapped.
        """
        all_internal_states = [
            ConversationState.UNCREATED,
            ConversationState.ACTIVE,
            ConversationState.CLOSED,
        ]
        
        for internal_state in all_internal_states:
            client_state = self.adapter._map_conversation_state(internal_state)
            self.assertIsInstance(client_state, ClientConversationState)


if __name__ == "__main__":
    unittest.main()
