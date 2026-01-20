"""
Unit tests for message delivery module.

References:
- Functional Specification (#6)
- State Machines (#7)
- Data Classification & Retention (#8)
- Lifecycle Playbooks (#15)
- Resolved Specs & Clarifications
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

from src.client.message_delivery import MessageDeliveryService
from src.shared.constants import (
    DEFAULT_MESSAGE_EXPIRATION_DAYS,
    MAX_DELIVERY_RETRIES,
    MAX_GROUP_SIZE,
    MAX_MESSAGE_PAYLOAD_SIZE_KB,
    MAX_OFFLINE_MESSAGES,
    MAX_OFFLINE_STORAGE_MB,
)
from src.shared.message_types import Message, MessageState


class TestMessageDeliveryService(unittest.TestCase):
    """Test cases for MessageDeliveryService per Functional Spec (#6) and State Machines (#7)."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.device_id = "test-device-001"
        self.encryption_service = Mock()
        self.storage_service = Mock()
        self.websocket_client = Mock()
        self.http_client = Mock()
        self.log_service = Mock()
        
        # Mock encryption service
        self.encryption_service.encrypt = Mock(return_value=b"encrypted_payload")
        self.encryption_service.decrypt = Mock(return_value=b"plaintext_content")
        
        self.service = MessageDeliveryService(
            device_id=self.device_id,
            encryption_service=self.encryption_service,
            storage_service=self.storage_service,
            websocket_client=self.websocket_client,
            http_client=self.http_client,
            log_service=self.log_service,
        )
    
    def test_create_message_success(self):
        """
        Test message creation per Functional Spec (#6), Section 4.2.
        
        Message should be encrypted on device and assigned metadata.
        """
        plaintext = b"Test message content"
        recipients = ["recipient-001", "recipient-002"]
        conversation_id = "conv-001"
        
        message = self.service.create_message(
            plaintext_content=plaintext,
            recipients=recipients,
            conversation_id=conversation_id,
        )
        
        # Verify message structure per Functional Spec (#6), Section 4.2
        self.assertIsNotNone(message.message_id)
        self.assertEqual(message.sender_id, self.device_id)
        self.assertEqual(message.recipients, recipients)
        self.assertEqual(message.conversation_id, conversation_id)
        self.assertEqual(message.state, MessageState.CREATED)
        self.assertEqual(message.retry_count, 0)
        
        # Verify encryption was called per Functional Spec (#6), Section 4.2
        self.encryption_service.encrypt.assert_called_once_with(plaintext)
        
        # Verify expiration timestamp per Resolved TBDs (default 7 days)
        expected_expiration = message.creation_timestamp + timedelta(
            days=DEFAULT_MESSAGE_EXPIRATION_DAYS
        )
        self.assertEqual(message.expiration_timestamp, expected_expiration)
    
    def test_create_message_max_group_size(self):
        """
        Test message creation with max group size per Resolved TBDs.
        
        Max 50 participants per conversation.
        """
        plaintext = b"Test message"
        recipients = [f"recipient-{i:03d}" for i in range(MAX_GROUP_SIZE)]
        conversation_id = "conv-001"
        
        # Should succeed with max group size
        message = self.service.create_message(
            plaintext_content=plaintext,
            recipients=recipients,
            conversation_id=conversation_id,
        )
        self.assertEqual(len(message.recipients), MAX_GROUP_SIZE)
        
        # Should fail with group size > 50
        recipients_over_limit = [f"recipient-{i:03d}" for i in range(MAX_GROUP_SIZE + 1)]
        with self.assertRaises(ValueError):
            self.service.create_message(
                plaintext_content=plaintext,
                recipients=recipients_over_limit,
                conversation_id=conversation_id,
            )
    
    def test_create_message_max_payload_size(self):
        """
        Test message creation with max payload size per Resolved TBDs.
        
        Max 50KB per message.
        """
        # Should succeed with max payload size
        plaintext = b"x" * (MAX_MESSAGE_PAYLOAD_SIZE_KB * 1024)
        recipients = ["recipient-001"]
        conversation_id = "conv-001"
        
        message = self.service.create_message(
            plaintext_content=plaintext,
            recipients=recipients,
            conversation_id=conversation_id,
        )
        self.assertIsNotNone(message)
        
        # Should fail with payload > 50KB
        plaintext_over_limit = b"x" * (MAX_MESSAGE_PAYLOAD_SIZE_KB * 1024 + 1)
        with self.assertRaises(ValueError):
            self.service.create_message(
                plaintext_content=plaintext_over_limit,
                recipients=recipients,
                conversation_id=conversation_id,
            )
    
    def test_send_message_websocket(self):
        """
        Test message sending via WebSocket per Resolved TBDs.
        
        WebSocket is preferred delivery mechanism.
        """
        message = self.service.create_message(
            plaintext_content=b"Test message",
            recipients=["recipient-001"],
            conversation_id="conv-001",
        )
        
        self.service._websocket_connected = True
        self.websocket_client.send = Mock()
        
        result = self.service.send_message(message)
        
        # Should transition to PENDING_DELIVERY per State Machines (#7), Section 3
        self.assertEqual(message.state, MessageState.PENDING_DELIVERY)
        self.assertTrue(result)
        self.websocket_client.send.assert_called_once()
    
    def test_send_message_rest_fallback(self):
        """
        Test message sending via REST fallback per Resolved TBDs.
        
        REST polling fallback when WebSocket unavailable.
        """
        message = self.service.create_message(
            plaintext_content=b"Test message",
            recipients=["recipient-001"],
            conversation_id="conv-001",
        )
        
        self.service._websocket_connected = False
        self.http_client.post = Mock(return_value=Mock(status_code=200, json=lambda: {"message_id": str(message.message_id), "status": "queued"}))
        
        result = self.service.send_message(message)
        
        # Should transition to PENDING_DELIVERY per State Machines (#7), Section 3
        self.assertEqual(message.state, MessageState.PENDING_DELIVERY)
        self.assertTrue(result)
        self.http_client.post.assert_called_once()
    
    def test_queue_message_offline(self):
        """
        Test offline message queuing per Functional Spec (#6), Section 10.
        
        Messages queued when network unavailable.
        """
        message = self.service.create_message(
            plaintext_content=b"Test message",
            recipients=["recipient-001"],
            conversation_id="conv-001",
        )
        
        self.service._websocket_connected = False
        self.service.http_client = None  # No network available
        
        result = self.service.send_message(message)
        
        # Should be queued offline
        self.assertFalse(result)
        self.assertIn(message.message_id, self.service._queued_messages)
    
    def test_offline_storage_limits(self):
        """
        Test offline storage limits per Resolved TBDs.
        
        Max 500 messages or 50MB per device.
        """
        # Create messages up to limit
        for i in range(MAX_OFFLINE_MESSAGES):
            message = self.service.create_message(
                plaintext_content=b"Test message",
                recipients=["recipient-001"],
                conversation_id=f"conv-{i:03d}",
            )
            self.service._queue_message_offline(message)
        
        # Should have queued messages
        self.assertEqual(len(self.service._queued_messages), MAX_OFFLINE_MESSAGES)
        
        # Next message should not be queued if storage full and no expired messages
        message_over_limit = self.service.create_message(
            plaintext_content=b"Test message",
            recipients=["recipient-001"],
            conversation_id="conv-over-limit",
        )
        self.service._queue_message_offline(message_over_limit)
        
        # Should still be at limit (message not queued or expired message evicted)
        self.assertLessEqual(len(self.service._queued_messages), MAX_OFFLINE_MESSAGES)
    
    def test_evict_expired_messages(self):
        """
        Test expired message eviction per Resolved Clarifications.
        
        Eviction applies only to expired messages.
        Oldest expired messages removed first.
        """
        # Create expired message
        expired_message = self.service.create_message(
            plaintext_content=b"Expired message",
            recipients=["recipient-001"],
            conversation_id="conv-expired",
        )
        expired_message.expiration_timestamp = datetime.utcnow() - timedelta(days=1)
        
        # Create unexpired message
        unexpired_message = self.service.create_message(
            plaintext_content=b"Unexpired message",
            recipients=["recipient-001"],
            conversation_id="conv-unexpired",
        )
        
        # Queue both messages
        self.service._queue_message_offline(expired_message)
        self.service._queue_message_offline(unexpired_message)
        
        # Evict expired messages
        evicted = self.service._evict_expired_messages()
        
        # Expired message should be evicted, unexpired should remain
        self.assertTrue(evicted)
        self.assertNotIn(expired_message.message_id, self.service._queued_messages)
        self.assertIn(unexpired_message.message_id, self.service._queued_messages)
    
    def test_receive_message_success(self):
        """
        Test message reception per Functional Spec (#6), Section 4.3.
        
        Message should be decrypted locally and stored encrypted at rest.
        """
        message_id = uuid4()
        encrypted_payload = b"encrypted_payload"
        sender_id = "sender-001"
        conversation_id = "conv-001"
        expiration_timestamp = datetime.utcnow() + timedelta(days=7)
        
        message = self.service.receive_message(
            message_id=message_id,
            encrypted_payload=encrypted_payload,
            sender_id=sender_id,
            conversation_id=conversation_id,
            expiration_timestamp=expiration_timestamp,
        )
        
        # Verify message structure per Functional Spec (#6), Section 4.3
        self.assertIsNotNone(message)
        self.assertEqual(message.message_id, message_id)
        self.assertEqual(message.sender_id, sender_id)
        self.assertEqual(message.state, MessageState.ACTIVE)
        
        # Verify decryption was called per Functional Spec (#6), Section 4.3
        self.encryption_service.decrypt.assert_called_once_with(encrypted_payload)
        
        # Verify storage was called per Functional Spec (#6), Section 4.3
        self.storage_service.store_message.assert_called_once_with(message_id, encrypted_payload)
    
    def test_receive_message_duplicate_id(self):
        """
        Test duplicate message detection per Resolved Clarifications.
        
        Duplicate detection: Message ID first.
        """
        message_id = uuid4()
        encrypted_payload = b"encrypted_payload"
        sender_id = "sender-001"
        conversation_id = "conv-001"
        expiration_timestamp = datetime.utcnow() + timedelta(days=7)
        
        # Receive message first time
        message1 = self.service.receive_message(
            message_id=message_id,
            encrypted_payload=encrypted_payload,
            sender_id=sender_id,
            conversation_id=conversation_id,
            expiration_timestamp=expiration_timestamp,
        )
        self.assertIsNotNone(message1)
        
        # Receive same message ID again (duplicate)
        message2 = self.service.receive_message(
            message_id=message_id,
            encrypted_payload=encrypted_payload,
            sender_id=sender_id,
            conversation_id=conversation_id,
            expiration_timestamp=expiration_timestamp,
        )
        
        # Should be None (duplicate discarded) per Resolved Clarifications
        self.assertIsNone(message2)
    
    def test_receive_message_expired(self):
        """
        Test expired message rejection per Functional Spec (#6), Section 4.4.
        
        Expired messages should not be processed.
        """
        message_id = uuid4()
        encrypted_payload = b"encrypted_payload"
        sender_id = "sender-001"
        conversation_id = "conv-001"
        expiration_timestamp = datetime.utcnow() - timedelta(days=1)  # Expired
        
        message = self.service.receive_message(
            message_id=message_id,
            encrypted_payload=encrypted_payload,
            sender_id=sender_id,
            conversation_id=conversation_id,
            expiration_timestamp=expiration_timestamp,
        )
        
        # Should be None (expired, not processed) per Functional Spec (#6), Section 4.4
        self.assertIsNone(message)
    
    def test_message_expiration(self):
        """
        Test message expiration per Functional Spec (#6), Section 4.4 and State Machines (#7), Section 7.
        
        Expired messages should be deleted from device storage and removed from UI.
        """
        message = self.service.create_message(
            plaintext_content=b"Test message",
            recipients=["recipient-001"],
            conversation_id="conv-001",
        )
        
        # Set expiration to past
        message.expiration_timestamp = datetime.utcnow() - timedelta(seconds=1)
        
        # Manually trigger expiration
        self.service._expire_message(message.message_id)
        
        # Message should be in EXPIRED state per State Machines (#7), Section 3
        self.assertEqual(message.state, MessageState.EXPIRED)
        
        # Should be deleted from storage per Functional Spec (#6), Section 4.4
        self.storage_service.delete_message.assert_called_once_with(message.message_id)
        
        # Should be removed from tracking
        self.assertNotIn(message.message_id, self.service._messages)
    
    def test_retry_limits(self):
        """
        Test retry limits per Resolved TBDs.
        
        Maximum 5 attempts before marking as Failed.
        """
        message = self.service.create_message(
            plaintext_content=b"Test message",
            recipients=["recipient-001"],
            conversation_id="conv-001",
        )
        
        # Queue message offline
        self.service._queue_message_offline(message)
        
        # Simulate retries up to limit
        for i in range(MAX_DELIVERY_RETRIES):
            queued = self.service._queued_messages[message.message_id]
            queued.message.retry_count = i
            queued.last_retry_at = datetime.utcnow()
        
        # Should not retry beyond limit
        queued = self.service._queued_messages[message.message_id]
        self.assertFalse(queued.should_retry())
        
        # Process queue should mark as failed
        self.service.process_offline_queue()
        
        # Message should be in FAILED state per State Machines (#7), Section 3
        self.assertEqual(message.state, MessageState.FAILED)


if __name__ == "__main__":
    unittest.main()
