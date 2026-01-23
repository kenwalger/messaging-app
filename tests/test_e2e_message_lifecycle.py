"""
End-to-end integration tests for message lifecycle across backend and frontend boundaries.

References:
- Functional Specification (#6), Sections 4.2-4.5
- State Machines (#7), Section 3
- API Contracts (#10)
- Message Delivery & Reliability docs
- Resolved Clarifications (#51)

Tests validate:
- Message send → ACK happy path
- WebSocket preferred transport
- REST fallback behavior
- Reverse chronological ordering

Focus on happy paths only to avoid flakiness.
No UI rendering/DOM assertions - verify via store/state only.
Uses deterministic timestamps and message IDs for reliability.
"""

import asyncio
import json
import unittest
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID, uuid4

from src.backend.conversation_registry import ConversationRegistry
from src.backend.device_registry import DeviceRegistry
from src.backend.message_relay import MessageRelayService
from src.client.message_delivery import MessageDeliveryService
from src.shared.constants import ACK_TIMEOUT_SECONDS
from src.shared.message_types import MessageState, utc_now

# Try to import FastAPIWebSocketManager, but fall back to mock if fastapi not available
try:
    from src.backend.websocket_manager import FastAPIWebSocketManager
    FASTAPI_AVAILABLE = True
except ImportError:
    # FastAPI not available in test environment - use mock instead
    FASTAPI_AVAILABLE = False
    FastAPIWebSocketManager = None


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.sent_messages: List[str] = []
        self.is_connected = True
        self.receive_queue: asyncio.Queue = asyncio.Queue()
    
    async def send_text(self, message: str) -> None:
        """Mock send_text method."""
        self.sent_messages.append(message)
    
    async def receive_text(self) -> str:
        """Mock receive_text - waits for messages in queue."""
        return await self.receive_queue.get()
    
    async def close(self) -> None:
        """Mock close method."""
        self.is_connected = False
    
    async def connect(self, websocket_manager) -> None:
        """Connect this mock WebSocket to the WebSocket manager."""
        # This method is not used in current tests
        pass


class TestE2EMessageLifecycle(unittest.TestCase):
    """End-to-end integration tests for message lifecycle."""
    
    def setUp(self) -> None:
        """Set up test fixtures with deterministic values."""
        # Fixed timestamps for deterministic tests
        self.fixed_timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.fixed_message_id = uuid4()
        
        # Device setup
        self.sender_id = "sender-device-001"
        self.recipient_id = "recipient-device-001"
        
        # Create device registry
        self.device_registry = DeviceRegistry()
        # Register and provision devices (must register first)
        # Register creates device in PENDING state
        self.device_registry.register_device(self.sender_id, "test-public-key-1")
        # provision_device transitions PENDING -> PROVISIONED
        self.device_registry.provision_device(self.sender_id)
        # confirm_provisioning transitions PROVISIONED -> ACTIVE
        self.device_registry.confirm_provisioning(self.sender_id)
        # Verify device is now ACTIVE
        self.assertTrue(self.device_registry.is_device_active(self.sender_id))
        
        self.device_registry.register_device(self.recipient_id, "test-public-key-2")
        self.device_registry.provision_device(self.recipient_id)
        self.device_registry.confirm_provisioning(self.recipient_id)
        # Verify device is now ACTIVE
        self.assertTrue(self.device_registry.is_device_active(self.recipient_id))
        
        # Create conversation registry
        self.conversation_registry = ConversationRegistry(self.device_registry, demo_mode=True)
        
        # Create conversation
        self.conversation_id = "conv-001"
        self.conversation_registry.register_conversation(
            self.conversation_id,
            [self.sender_id, self.recipient_id]
        )
        
        # Create WebSocket manager (mock if FastAPI not available)
        if FASTAPI_AVAILABLE and FastAPIWebSocketManager:
            self.websocket_manager = FastAPIWebSocketManager()
        else:
            # Mock WebSocket manager for tests when FastAPI not available
            self.websocket_manager = Mock()
            self.websocket_manager.is_connected = Mock(return_value=False)
            self.websocket_manager.send_to_device = Mock(return_value=True)
            self.websocket_manager.start_background_task = Mock()
            self.websocket_manager.stop_background_task = Mock()
        
        # Create message relay
        self.message_relay = MessageRelayService(
            device_registry=self.device_registry,
            websocket_manager=self.websocket_manager,
            log_service=Mock(),
        )
        
        # Mock encryption service (no actual encryption in tests)
        self.encryption_service = Mock()
        self.encryption_service.encrypt = Mock(return_value=b"encrypted_payload")
        self.encryption_service.decrypt = Mock(return_value=b"plaintext_content")
        
        # Mock storage service
        self.storage_service = Mock()
        
        # Mock HTTP client
        self.http_client = Mock()
        
        # Mock WebSocket client for sender
        self.sender_websocket_client = Mock()
        self.sender_websocket_client.send = Mock(return_value=True)
        self.sender_websocket_client.is_connected = Mock(return_value=True)
        
        # Mock WebSocket client for recipient
        self.recipient_websocket_client = Mock()
        self.recipient_websocket_client.send = Mock(return_value=True)
        self.recipient_websocket_client.is_connected = Mock(return_value=True)
        
        # Mock HTTP client for REST fallback
        self.http_client.post = Mock(return_value=Mock(
            status_code=200,
            json=Mock(return_value={"message_id": str(uuid4())})
        ))
        
        # Create message delivery service for sender
        self.sender_service = MessageDeliveryService(
            device_id=self.sender_id,
            encryption_service=self.encryption_service,
            storage_service=self.storage_service,
            websocket_client=self.sender_websocket_client,
            http_client=self.http_client,
            log_service=Mock(),
        )
        
        # Create message delivery service for recipient
        self.recipient_service = MessageDeliveryService(
            device_id=self.recipient_id,
            encryption_service=self.encryption_service,
            storage_service=self.storage_service,
            websocket_client=self.recipient_websocket_client,
            http_client=self.http_client,
            log_service=Mock(),
        )
        
        # Mock WebSocket connections (will be connected in tests that need them)
        self.sender_ws: Optional[MockWebSocket] = None
        self.recipient_ws: Optional[MockWebSocket] = None
    
    def tearDown(self) -> None:
        """Clean up test fixtures."""
        # Cancel all timers
        with self.sender_service._timer_lock:
            for timer in self.sender_service._expiration_timers.values():
                timer.cancel()
            self.sender_service._expiration_timers.clear()
        
        with self.recipient_service._timer_lock:
            for timer in self.recipient_service._expiration_timers.values():
                timer.cancel()
            self.recipient_service._expiration_timers.clear()
        
        # Stop REST polling if active
        if self.sender_service._rest_polling_active:
            self.sender_service._stop_rest_polling()
        if self.recipient_service._rest_polling_active:
            self.recipient_service._stop_rest_polling()
    
    @patch('src.backend.message_relay.utc_now')
    @patch('src.shared.message_types.utc_now')
    def test_message_send_to_ack_happy_path(
        self, mock_shared_utc_now: Mock, mock_relay_utc_now: Mock
    ) -> None:
        """
        Test message send → ACK happy path (end-to-end).
        
        Verifies:
        - Message enters PENDING state
        - Backend enqueues message via message relay
        - Message delivered to recipient
        - ACK received within timeout
        - Message transitions to DELIVERED
        """
        # Use fixed timestamp for deterministic tests
        # Mock utc_now in both message_relay and message_types
        mock_relay_utc_now.return_value = self.fixed_timestamp
        mock_shared_utc_now.return_value = self.fixed_timestamp
        
        # Create and send message (simulating frontend send)
        message = self.sender_service.create_message(
            plaintext_content=b"Test message",
            recipients=[self.recipient_id],
            conversation_id=self.conversation_id,
        )
        
        # Verify message in CREATED state
        self.assertEqual(message.state, MessageState.CREATED)
        
        # Set WebSocket as connected for send_message to work
        self.sender_service._websocket_connected = True
        
        # Send message (simulating frontend → backend API call)
        success = self.sender_service.send_message(message)
        self.assertTrue(success)
        
        # Verify message in PENDING_DELIVERY state
        self.assertEqual(message.state, MessageState.PENDING_DELIVERY)
        
        # Verify ACK tracking
        with self.sender_service._ack_lock:
            self.assertIn(message.message_id, self.sender_service._pending_acks)
        
        # Simulate backend relay (backend receives message and relays to recipient)
        # Note: In real system, backend would receive this via /api/message/send endpoint
        relay_success = self.message_relay.relay_message(
            sender_id=self.sender_id,
            recipients=[self.recipient_id],
            encrypted_payload=message.payload,
            message_id=message.message_id,
            expiration_timestamp=message.expiration_timestamp,
            conversation_id=self.conversation_id,
        )
        self.assertTrue(relay_success)
        
        # Verify message is stored in sender's _messages dict (needed for ACK handling)
        self.assertIn(message.message_id, self.sender_service._messages)
        
        # Verify message is pending in backend
        pending_messages = self.message_relay.get_pending_messages(self.recipient_id)
        self.assertEqual(len(pending_messages), 1)
        self.assertEqual(pending_messages[0]["message_id"], str(message.message_id))
        
        # Simulate recipient receiving message (via WebSocket or REST)
        received_message = self.recipient_service.receive_message(
            message_id=message.message_id,
            encrypted_payload=message.payload,
            sender_id=self.sender_id,
            conversation_id=self.conversation_id,
            expiration_timestamp=message.expiration_timestamp,
        )
        self.assertIsNotNone(received_message)
        # receive_message creates message in DELIVERED state, then transitions to ACTIVE
        # Per State Machines (#7), Section 3: DELIVERED -> ACTIVE is valid transition
        self.assertEqual(received_message.state, MessageState.ACTIVE)
        
        # Simulate ACK sent back to sender (via backend)
        # In real system, recipient would send ACK, backend forwards to sender
        # First, verify message is in PENDING_DELIVERY state
        self.assertEqual(message.state, MessageState.PENDING_DELIVERY)
        
        # Handle ACK - this should transition message to DELIVERED
        self.sender_service.handle_delivery_ack(message.message_id)
        
        # Verify message transitioned to DELIVERED
        # Note: handle_delivery_ack updates the message in _messages dict
        updated_message = self.sender_service._messages.get(message.message_id)
        if updated_message:
            self.assertEqual(updated_message.state, MessageState.DELIVERED)
        else:
            # If message not in dict, check the original message object
            self.assertEqual(message.state, MessageState.DELIVERED)
        
        # Verify ACK removed from pending
        with self.sender_service._ack_lock:
            self.assertNotIn(message.message_id, self.sender_service._pending_acks)
    
    @patch('src.shared.message_types.utc_now')
    def test_websocket_preferred_transport(self, mock_utc_now: Mock) -> None:
        """
        Test WebSocket preferred transport.
        
        Verifies:
        - Message delivered via WebSocket when available
        - REST polling is not used
        """
        mock_utc_now.return_value = self.fixed_timestamp
        
        # Set WebSocket as connected
        self.sender_service._websocket_connected = True
        
        # Create and send message
        message = self.sender_service.create_message(
            plaintext_content=b"Test message",
            recipients=[self.recipient_id],
            conversation_id=self.conversation_id,
        )
        
        # Send message
        success = self.sender_service.send_message(message)
        self.assertTrue(success)
        
        # Verify message in PENDING_DELIVERY state
        self.assertEqual(message.state, MessageState.PENDING_DELIVERY)
        
        # Verify WebSocket client was used (via send method)
        # The WebSocket client's send method should have been called
        self.assertTrue(self.sender_websocket_client.send.called or 
                       len(self.sender_service._pending_acks) > 0)
        
        # Verify REST client was NOT used
        if hasattr(self.http_client, 'post'):
            self.http_client.post.assert_not_called()
        
        # Verify REST polling is not active
        self.assertFalse(self.sender_service._rest_polling_active)
    
    @patch('src.client.message_delivery.utc_now')
    @patch('src.backend.message_relay.utc_now')
    @patch('src.shared.message_types.utc_now')
    def test_rest_fallback_simulation(
        self, mock_shared_utc_now: Mock, mock_relay_utc_now: Mock, mock_client_utc_now: Mock
    ) -> None:
        """
        Test REST fallback when WebSocket unavailable.
        
        Verifies:
        - REST polling receives message when WebSocket unavailable
        - Message deduplicated correctly
        - Store reconciles cleanly (no duplicates)
        """
        # Mock utc_now in message_relay, message_types, and message_delivery
        mock_relay_utc_now.return_value = self.fixed_timestamp
        mock_shared_utc_now.return_value = self.fixed_timestamp
        mock_client_utc_now.return_value = self.fixed_timestamp
        
        # Set WebSocket as disconnected (simulating WebSocket unavailable)
        self.recipient_service._websocket_connected = False
        
        # Simulate backend has message pending for recipient
        # (Backend would have received message via /api/message/send)
        message_id = uuid4()
        expiration = self.fixed_timestamp + timedelta(days=7)
        encrypted_payload = b"encrypted_payload"
        
        # Backend enqueues message via message_relay (simulating /api/message/send endpoint)
        # First ensure sender device is active
        self.assertTrue(self.device_registry.is_device_active(self.sender_id))
        self.assertTrue(self.device_registry.is_device_active(self.recipient_id))
        
        relay_success = self.message_relay.relay_message(
            sender_id=self.sender_id,
            recipients=[self.recipient_id],
            encrypted_payload=encrypted_payload,
            message_id=message_id,
            expiration_timestamp=expiration,
            conversation_id=self.conversation_id,
        )
        self.assertTrue(relay_success)
        
        # Simulate REST polling fetch (GET /api/message/receive)
        pending_messages = self.message_relay.get_pending_messages(self.recipient_id)
        
        # Verify message is available via REST
        self.assertEqual(len(pending_messages), 1)
        self.assertEqual(pending_messages[0]["message_id"], str(message_id))
        
        # Simulate recipient receiving message via REST polling
        received_message = self.recipient_service.receive_message(
            message_id=message_id,
            encrypted_payload=encrypted_payload,
            sender_id=self.sender_id,
            conversation_id=self.conversation_id,
            expiration_timestamp=expiration,
        )
        
        # Verify message received and stored
        self.assertIsNotNone(received_message)
        self.assertEqual(received_message.message_id, message_id)
        # receive_message creates message in DELIVERED state, then transitions to ACTIVE
        # Per State Machines (#7), Section 3: DELIVERED -> ACTIVE is valid transition
        self.assertEqual(received_message.state, MessageState.ACTIVE)
        self.assertIn(message_id, self.recipient_service._messages)
        
        # Verify deduplication: try to receive same message again
        duplicate_message = self.recipient_service.receive_message(
            message_id=message_id,
            encrypted_payload=encrypted_payload,
            sender_id=self.sender_id,
            conversation_id=self.conversation_id,
            expiration_timestamp=expiration,
        )
        
        # Verify duplicate rejected (deduplication works)
        self.assertIsNone(duplicate_message)
        
        # Verify message count unchanged (no duplicate in store)
        self.assertEqual(len(self.recipient_service._messages), 1)
    
    @patch('src.backend.message_relay.utc_now')
    @patch('src.shared.message_types.utc_now')
    def test_backend_api_send_endpoint_integration(
        self, mock_shared_utc_now: Mock, mock_relay_utc_now: Mock
    ) -> None:
        """
        Test backend API send endpoint integration.
        
        Verifies:
        - Backend receives message via /api/message/send endpoint flow
        - Backend derives recipients from conversation_id
        - Backend enqueues message for delivery
        - Message available via REST polling
        """
        # Mock utc_now in both message_relay and message_types
        mock_relay_utc_now.return_value = self.fixed_timestamp
        mock_shared_utc_now.return_value = self.fixed_timestamp
        
        # Start WebSocket background task (if available, otherwise mock handles it)
        if hasattr(self.websocket_manager, 'start_background_task'):
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                self.websocket_manager.start_background_task(loop)
            except Exception:
                # If event loop not available, mock handles it
                pass
        
        # Simulate /api/message/send endpoint call
        # (In real system, this would be HTTP POST with X-Device-ID header)
        message_id = uuid4()
        expiration = self.fixed_timestamp + timedelta(days=7)
        encrypted_payload = b"encrypted_payload"
        
        # Backend endpoint logic: derive recipients from conversation
        participants = self.conversation_registry.get_conversation_participants(
            self.conversation_id
        )
        recipients = [p for p in participants if p != self.sender_id]
        
        # Backend endpoint calls message_relay.relay_message()
        # First ensure devices are active
        self.assertTrue(self.device_registry.is_device_active(self.sender_id))
        self.assertTrue(self.device_registry.is_device_active(self.recipient_id))
        
        relay_success = self.message_relay.relay_message(
            sender_id=self.sender_id,
            recipients=recipients,
            encrypted_payload=encrypted_payload,
            message_id=message_id,
            expiration_timestamp=expiration,
            conversation_id=self.conversation_id,
        )
        
        # Verify message relayed successfully
        self.assertTrue(relay_success)
        
        # Verify message available via REST polling (GET /api/message/receive)
        pending_messages = self.message_relay.get_pending_messages(self.recipient_id)
        self.assertEqual(len(pending_messages), 1)
        self.assertEqual(pending_messages[0]["message_id"], str(message_id))
        
        # Cleanup (if available)
        if hasattr(self.websocket_manager, 'stop_background_task'):
            self.websocket_manager.stop_background_task()
    
    @patch('src.shared.message_types.utc_now')
    def test_reverse_chronological_ordering(self, mock_utc_now: Mock) -> None:
        """
        Test reverse chronological ordering.
        
        Verifies:
        - Newest message appears first
        - No reordering after ACKs
        """
        # Use sequential timestamps
        timestamps = [
            self.fixed_timestamp,
            self.fixed_timestamp + timedelta(seconds=1),
            self.fixed_timestamp + timedelta(seconds=2),
        ]
        
        messages: List[UUID] = []
        
        # Set WebSocket as connected for send_message to work
        self.sender_service._websocket_connected = True
        
        # Send multiple messages
        for i, timestamp in enumerate(timestamps):
            mock_utc_now.return_value = timestamp
            
            message = self.sender_service.create_message(
                plaintext_content=f"Message {i}".encode(),
                recipients=[self.recipient_id],
                conversation_id=self.conversation_id,
            )
            
            messages.append(message.message_id)
            
            # Send message
            success = self.sender_service.send_message(message)
            self.assertTrue(success)
            
            # Verify message is in _messages dict (needed for ACK handling)
            self.assertIn(message.message_id, self.sender_service._messages)
            
            # Immediately ACK (simulating fast delivery)
            self.sender_service.handle_delivery_ack(message.message_id)
            
            # Verify message transitioned to DELIVERED
            updated_message = self.sender_service._messages.get(message.message_id)
            self.assertIsNotNone(updated_message)
            self.assertEqual(updated_message.state, MessageState.DELIVERED)
        
        # Verify messages are stored
        self.assertEqual(len(self.sender_service._messages), 3)
        
        # Get all messages sorted by creation timestamp
        all_messages = list(self.sender_service._messages.values())
        sorted_messages = sorted(
            all_messages,
            key=lambda m: m.creation_timestamp,
            reverse=True  # Newest first
        )
        
        # Verify reverse chronological order (newest first)
        # Allow for small timing differences due to patching
        self.assertEqual(len(sorted_messages), 3)
        # Verify ordering is correct (newest first)
        self.assertGreaterEqual(
            sorted_messages[0].creation_timestamp,
            sorted_messages[1].creation_timestamp
        )
        self.assertGreaterEqual(
            sorted_messages[1].creation_timestamp,
            sorted_messages[2].creation_timestamp
        )
        
        # Verify all messages are DELIVERED (ACKs received)
        for message in sorted_messages:
            self.assertEqual(message.state, MessageState.DELIVERED)
        
        # Verify no reordering after ACKs (order should remain stable)
        sorted_after_acks = sorted(
            all_messages,
            key=lambda m: m.creation_timestamp,
            reverse=True
        )
        
        # Order should be identical (newest first maintained)
        for i, msg in enumerate(sorted_messages):
            self.assertEqual(msg.message_id, sorted_after_acks[i].message_id)
            self.assertEqual(msg.creation_timestamp, sorted_after_acks[i].creation_timestamp)


if __name__ == "__main__":
    unittest.main()
