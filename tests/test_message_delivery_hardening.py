"""
Unit tests for message delivery reliability hardening.

References:
- Functional Specification (#6), Sections 4.2-4.5
- State Machines (#7), Section 3
- Lifecycle Playbooks (#15), Section 5
- Resolved Specs & Clarifications (#51)
"""

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

from src.client.message_delivery import MessageDeliveryService
from src.shared.constants import (
    ACK_TIMEOUT_SECONDS,
    MAX_DELIVERY_RETRIES,
    REST_POLLING_INTERVAL_SECONDS,
    WEBSOCKET_RECONNECT_TIMEOUT_SECONDS,
)
from src.shared.message_types import Message, MessageState, utc_now


class TestMessageDeliveryHardening(unittest.TestCase):
    """Test cases for message delivery reliability hardening per Resolved Clarifications."""
    
    def setUp(self) -> None:
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
    
    def tearDown(self) -> None:
        """Clean up test fixtures."""
        # Cancel all timers to prevent pytest from hanging
        with self.service._timer_lock:
            for timer in self.service._expiration_timers.values():
                timer.cancel()
            self.service._expiration_timers.clear()
        
        # Stop REST polling if active
        if self.service._rest_polling_active:
            self.service._stop_rest_polling()
    
    def test_websocket_delivery_with_ack(self) -> None:
        """
        Test successful WebSocket delivery with ACK per Resolved Clarifications (#51).
        
        Message should transition from PENDING_DELIVERY to DELIVERED on ACK.
        """
        # Set WebSocket as connected
        self.service._websocket_connected = True
        
        # Create and send message
        message = self.service.create_message(
            plaintext_content=b"Test message",
            recipients=["recipient-001"],
            conversation_id="conv-001",
        )
        
        # Send via WebSocket
        success = self.service.send_message(message)
        self.assertTrue(success)
        
        # Verify message in PENDING_DELIVERY state
        self.assertEqual(message.state, MessageState.PENDING_DELIVERY)
        
        # Verify ACK tracking
        with self.service._ack_lock:
            self.assertIn(message.message_id, self.service._pending_acks)
        
        # Handle ACK
        self.service.handle_delivery_ack(message.message_id)
        
        # Verify message transitioned to DELIVERED
        self.assertEqual(message.state, MessageState.DELIVERED)
        
        # Verify ACK removed from pending
        with self.service._ack_lock:
            self.assertNotIn(message.message_id, self.service._pending_acks)
    
    def test_ack_timeout_retry(self) -> None:
        """
        Test ACK timeout triggers retry with exponential backoff per Resolved Clarifications (#51).
        
        If ACK not received within timeout, message should be retried.
        """
        # Set WebSocket as connected
        self.service._websocket_connected = True
        
        # Create and send message
        message = self.service.create_message(
            plaintext_content=b"Test message",
            recipients=["recipient-001"],
            conversation_id="conv-001",
        )
        
        # Send via WebSocket
        self.service.send_message(message)
        
        # Verify ACK tracking
        with self.service._ack_lock:
            self.assertIn(message.message_id, self.service._pending_acks)
        
        # Simulate ACK timeout
        self.service._handle_ack_timeout(message.message_id)
        
        # Verify retry scheduled (retry_count incremented)
        self.assertGreater(message.retry_count, 0)
        
        # Verify ACK removed from pending
        with self.service._ack_lock:
            self.assertNotIn(message.message_id, self.service._pending_acks)
    
    def test_websocket_disconnect_rest_fallback(self) -> None:
        """
        Test WebSocket disconnect triggers REST polling fallback per Resolved Clarifications (#51).
        
        After >15s disconnect, should fallback to REST polling every 30s.
        """
        # Set WebSocket as connected initially
        self.service._websocket_connected = True
        
        # Disconnect WebSocket
        self.service.handle_websocket_disconnect()
        
        # Verify WebSocket disconnected
        self.assertFalse(self.service._websocket_connected)
        
        # Verify reconnect scheduled
        self.assertIsNotNone(self.service._websocket_reconnect_timer)
        
        # Simulate timeout (>15s) - trigger fallback
        self.service._check_websocket_reconnect_fallback()
        
        # Verify REST polling started
        self.assertTrue(self.service._rest_polling_active)
        self.assertIsNotNone(self.service._rest_polling_thread)
    
    def test_retry_exhaustion_marks_failed(self) -> None:
        """
        Test retry exhaustion marks message as FAILED per Lifecycle Playbooks (#15).
        
        After 5 retry attempts, message should be marked as FAILED.
        """
        # Create message
        message = self.service.create_message(
            plaintext_content=b"Test message",
            recipients=["recipient-001"],
            conversation_id="conv-001",
        )
        
        # Set retry count to max
        message.retry_count = MAX_DELIVERY_RETRIES
        
        # Attempt retry (should mark as failed)
        self.service._attempt_message_retry(message.message_id)
        
        # Verify message marked as FAILED
        self.assertEqual(message.state, MessageState.FAILED)
        
        # Verify failure logged
        self.log_service.log_event.assert_called()
        call_args = self.log_service.log_event.call_args
        self.assertEqual(call_args[0][0], "delivery_failed")
    
    def test_expired_message_rejection_on_receive(self) -> None:
        """
        Test expired messages are rejected on receive per Functional Spec (#6), Section 4.4.
        
        Expired messages should not be processed.
        """
        # Create expired message
        expired_timestamp = utc_now() - timedelta(days=1)
        
        # Attempt to receive expired message
        result = self.service.receive_message(
            message_id=uuid4(),
            encrypted_payload=b"encrypted_payload",
            sender_id="sender-001",
            conversation_id="conv-001",
            expiration_timestamp=expired_timestamp,
        )
        
        # Verify message rejected (None returned)
        self.assertIsNone(result)
    
    def test_expired_message_not_queued_offline(self) -> None:
        """
        Test expired messages are not queued offline per Resolved Clarifications (#39).
        
        Expired messages should be rejected immediately, not queued.
        """
        # Create expired message
        message = self.service.create_message(
            plaintext_content=b"Test message",
            recipients=["recipient-001"],
            conversation_id="conv-001",
        )
        message.expiration_timestamp = utc_now() - timedelta(days=1)
        
        # Attempt to queue offline
        initial_queue_size = len(self.service._queued_messages)
        self.service._queue_message_offline(message)
        
        # Verify message not queued
        self.assertEqual(len(self.service._queued_messages), initial_queue_size)
    
    def test_duplicate_message_id_suppression(self) -> None:
        """
        Test duplicate message ID suppression per Resolved Clarifications (#35).
        
        Primary duplicate detection: Message ID comparison.
        """
        message_id = uuid4()
        
        # Receive first message
        result1 = self.service.receive_message(
            message_id=message_id,
            encrypted_payload=b"encrypted_payload_1",
            sender_id="sender-001",
            conversation_id="conv-001",
            expiration_timestamp=utc_now() + timedelta(days=7),
        )
        
        # Verify first message received
        self.assertIsNotNone(result1)
        
        # Attempt to receive duplicate (same message ID)
        result2 = self.service.receive_message(
            message_id=message_id,
            encrypted_payload=b"encrypted_payload_2",  # Different payload
            sender_id="sender-001",
            conversation_id="conv-001",
            expiration_timestamp=utc_now() + timedelta(days=7),
        )
        
        # Verify duplicate rejected (None returned)
        self.assertIsNone(result2)
    
    def test_duplicate_content_hash_suppression(self) -> None:
        """
        Test duplicate content hash suppression per Resolved Clarifications (#35).
        
        Secondary duplicate detection: Content hash comparison.
        """
        encrypted_payload = b"encrypted_payload_same"
        
        # Receive first message
        result1 = self.service.receive_message(
            message_id=uuid4(),
            encrypted_payload=encrypted_payload,
            sender_id="sender-001",
            conversation_id="conv-001",
            expiration_timestamp=utc_now() + timedelta(days=7),
        )
        
        # Verify first message received
        self.assertIsNotNone(result1)
        
        # Attempt to receive duplicate (same content hash, different message ID)
        result2 = self.service.receive_message(
            message_id=uuid4(),  # Different message ID
            encrypted_payload=encrypted_payload,  # Same payload
            sender_id="sender-001",
            conversation_id="conv-001",
            expiration_timestamp=utc_now() + timedelta(days=7),
        )
        
        # Verify duplicate rejected (None returned)
        self.assertIsNone(result2)
    
    def test_exponential_backoff_calculation(self) -> None:
        """
        Test exponential backoff calculation per Lifecycle Playbooks (#15).
        
        Backoff delay should increase exponentially: base * 2^retry_count.
        """
        # Test backoff delays
        delay_0 = self.service._calculate_backoff_delay(0)
        delay_1 = self.service._calculate_backoff_delay(1)
        delay_2 = self.service._calculate_backoff_delay(2)
        delay_3 = self.service._calculate_backoff_delay(3)
        
        # Verify exponential increase
        self.assertLess(delay_0, delay_1)
        self.assertLess(delay_1, delay_2)
        self.assertLess(delay_2, delay_3)
        
        # Verify specific values (base = 1s)
        self.assertEqual(delay_0, 1.0)  # 1 * 2^0 = 1
        self.assertEqual(delay_1, 2.0)  # 1 * 2^1 = 2
        self.assertEqual(delay_2, 4.0)  # 1 * 2^2 = 4
        self.assertEqual(delay_3, 8.0)  # 1 * 2^3 = 8
    
    def test_rest_polling_respects_expiration(self) -> None:
        """
        Test REST polling respects expiration rules per Functional Spec (#6), Section 4.4.
        
        Expired messages from polling should be rejected.
        """
        # Mock HTTP client response with expired message
        expired_timestamp = utc_now() - timedelta(days=1)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": [
                {
                    "message_id": str(uuid4()),
                    "payload": b"encrypted".hex(),
                    "sender_id": "sender-001",
                    "conversation_id": "conv-001",
                    "expiration": expired_timestamp.isoformat(),
                }
            ]
        }
        self.http_client.get = Mock(return_value=mock_response)
        
        # Set stop event to exit loop after one iteration
        self.service._rest_polling_stop_event.set()
        
        # Process one polling cycle (will exit immediately due to stop event)
        # But first set active flag
        self.service._rest_polling_active = True
        
        # Manually process one message from the mock response
        # (simulating what the loop would do)
        response = self.http_client.get.return_value
        if response.status_code == 200:
            response_data = response.json()
            messages = response_data.get("messages", [])
            for msg_data in messages:
                msg_id = uuid4()
                encrypted_payload = bytes.fromhex(msg_data["payload"])
                sender_id = msg_data["sender_id"]
                conversation_id = msg_data.get("conversation_id", "")
                expiration_timestamp = datetime.fromisoformat(msg_data["expiration"])
                
                # Attempt to receive (should reject expired)
                result = self.service.receive_message(
                    message_id=msg_id,
                    encrypted_payload=encrypted_payload,
                    sender_id=sender_id,
                    conversation_id=conversation_id,
                    expiration_timestamp=expiration_timestamp,
                )
                
                # Verify expired message not received
                self.assertIsNone(result)
        
        # Verify no messages stored
        self.assertEqual(len(self.service._messages), 0)
    
    def test_websocket_reconnect_exponential_backoff(self) -> None:
        """
        Test WebSocket reconnect uses exponential backoff per Resolved Clarifications (#51).
        
        Reconnect attempts should use exponential backoff delays.
        """
        # Disconnect WebSocket
        self.service.handle_websocket_disconnect()
        
        # Verify reconnect scheduled
        self.assertIsNotNone(self.service._websocket_reconnect_timer)
        
        # Verify reconnect attempts tracked
        self.assertEqual(self.service._websocket_reconnect_attempts, 0)
        
        # Simulate reconnect attempt
        self.service._attempt_websocket_reconnect()
        
        # Verify reconnect attempts incremented
        self.assertEqual(self.service._websocket_reconnect_attempts, 1)
        
        # Verify another reconnect scheduled (exponential backoff)
        self.assertIsNotNone(self.service._websocket_reconnect_timer)
    
    def test_rest_polling_stops_on_websocket_connect(self) -> None:
        """
        Test REST polling stops when WebSocket reconnects per Resolved TBDs (#18).
        
        WebSocket is preferred, so REST polling should stop when WebSocket connects.
        """
        # Start REST polling
        self.service._start_rest_polling()
        self.assertTrue(self.service._rest_polling_active)
        
        # Simulate WebSocket connection
        self.service.handle_websocket_connect()
        
        # Verify REST polling stopped
        self.assertFalse(self.service._rest_polling_active)


if __name__ == "__main__":
    unittest.main()
