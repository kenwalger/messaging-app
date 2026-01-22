"""
Unit tests for /api/message/send endpoint.

References:
- API Contracts (#10), Section 3.3
- Functional Specification (#6), Section 4.2
- State Machines (#7), Section 3
- Logging & Observability (#14)
"""

import base64
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from src.backend.conversation_registry import ConversationRegistry
from src.backend.device_registry import DeviceRegistry
from src.backend.logging_service import LoggingService
from src.backend.message_relay import MessageRelayService
from src.backend.server import app
from src.backend.websocket_manager import FastAPIWebSocketManager
from src.shared.constants import (
    CLOCK_SKEW_TOLERANCE_MINUTES,
    DEFAULT_MESSAGE_EXPIRATION_DAYS,
    MAX_MESSAGE_PAYLOAD_SIZE_KB,
)
from src.shared.conversation_types import ConversationState
from src.shared.message_types import utc_now


@pytest.fixture
def device_registry() -> DeviceRegistry:
    """Create device registry for testing."""
    registry = DeviceRegistry()
    # Register and activate test devices
    registry.register_device("sender-001", "public-key-1", "controller-1")
    registry.provision_device("sender-001")
    registry.confirm_provisioning("sender-001")
    registry.register_device("recipient-001", "public-key-2", "controller-1")
    registry.provision_device("recipient-001")
    registry.confirm_provisioning("recipient-001")
    return registry


@pytest.fixture
def conversation_registry(device_registry: DeviceRegistry) -> ConversationRegistry:
    """Create conversation registry for testing."""
    registry = ConversationRegistry(device_registry)
    # Register test conversation
    registry.register_conversation("conv-001", ["sender-001", "recipient-001"])
    return registry


@pytest.fixture
def websocket_manager() -> FastAPIWebSocketManager:
    """Create WebSocket manager for testing."""
    return FastAPIWebSocketManager()


@pytest.fixture
def message_relay(
    device_registry: DeviceRegistry, websocket_manager: FastAPIWebSocketManager
) -> MessageRelayService:
    """Create message relay service for testing."""
    return MessageRelayService(
        device_registry=device_registry,
        websocket_manager=websocket_manager,
        log_service=LoggingService(),
    )


@pytest.fixture
def logging_service() -> LoggingService:
    """Create logging service for testing."""
    return LoggingService()


@pytest.fixture
def client(
    device_registry: DeviceRegistry,
    conversation_registry: ConversationRegistry,
    message_relay: MessageRelayService,
    logging_service: LoggingService,
) -> TestClient:
    """Create test client with mocked dependencies."""
    # Patch global service getters
    with patch("src.backend.server.get_device_registry", return_value=device_registry), \
         patch("src.backend.server.get_conversation_registry", return_value=conversation_registry), \
         patch("src.backend.server.get_message_relay", return_value=message_relay), \
         patch("src.backend.server.get_logging_service", return_value=logging_service):
        yield TestClient(app)


class TestMessageSendEndpoint:
    """Tests for POST /api/message/send endpoint."""
    
    def test_send_message_success(self, client: TestClient) -> None:
        """Test successful message send returns 202 Accepted."""
        message_id = str(uuid4())
        timestamp = utc_now().isoformat()
        expiration = (utc_now() + timedelta(days=7)).isoformat()
        payload = base64.b64encode(b"test message payload").decode("utf-8")
        
        response = client.post(
            "/api/message/send",
            json={
                "message_id": message_id,
                "conversation_id": "conv-001",
                "payload": payload,
                "timestamp": timestamp,
                "expiration": expiration,
            },
            headers={"X-Device-ID": "sender-001"},
        )
        
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert data["message_id"] == message_id
    
    def test_send_message_missing_message_id(self, client: TestClient) -> None:
        """Test send message with missing message_id returns 400."""
        timestamp = utc_now().isoformat()
        payload = base64.b64encode(b"test message").decode("utf-8")
        
        response = client.post(
            "/api/message/send",
            json={
                "conversation_id": "conv-001",
                "payload": payload,
                "timestamp": timestamp,
            },
            headers={"X-Device-ID": "sender-001"},
        )
        
        assert response.status_code == 400
        assert "message_id is required" in response.json()["detail"]
    
    def test_send_message_missing_conversation_id(self, client: TestClient) -> None:
        """Test send message with missing conversation_id returns 400."""
        message_id = str(uuid4())
        timestamp = utc_now().isoformat()
        payload = base64.b64encode(b"test message").decode("utf-8")
        
        response = client.post(
            "/api/message/send",
            json={
                "message_id": message_id,
                "payload": payload,
                "timestamp": timestamp,
            },
            headers={"X-Device-ID": "sender-001"},
        )
        
        assert response.status_code == 400
        assert "conversation_id is required" in response.json()["detail"]
    
    def test_send_message_missing_timestamp(self, client: TestClient) -> None:
        """Test send message with missing timestamp returns 400."""
        message_id = str(uuid4())
        payload = base64.b64encode(b"test message").decode("utf-8")
        
        response = client.post(
            "/api/message/send",
            json={
                "message_id": message_id,
                "conversation_id": "conv-001",
                "payload": payload,
            },
            headers={"X-Device-ID": "sender-001"},
        )
        
        assert response.status_code == 400
        assert "timestamp is required" in response.json()["detail"]
    
    def test_send_message_expired_timestamp(self, client: TestClient) -> None:
        """Test send message with expired timestamp returns 400."""
        message_id = str(uuid4())
        # Timestamp expired beyond clock skew tolerance
        expired_timestamp = (
            utc_now() - timedelta(minutes=CLOCK_SKEW_TOLERANCE_MINUTES + 1)
        ).isoformat()
        payload = base64.b64encode(b"test message").decode("utf-8")
        
        response = client.post(
            "/api/message/send",
            json={
                "message_id": message_id,
                "conversation_id": "conv-001",
                "payload": payload,
                "timestamp": expired_timestamp,
            },
            headers={"X-Device-ID": "sender-001"},
        )
        
        assert response.status_code == 400
        assert "timestamp is expired" in response.json()["detail"]
    
    def test_send_message_invalid_message_id(self, client: TestClient) -> None:
        """Test send message with invalid message_id format returns 400."""
        timestamp = utc_now().isoformat()
        payload = base64.b64encode(b"test message").decode("utf-8")
        
        response = client.post(
            "/api/message/send",
            json={
                "message_id": "not-a-uuid",
                "conversation_id": "conv-001",
                "payload": payload,
                "timestamp": timestamp,
            },
            headers={"X-Device-ID": "sender-001"},
        )
        
        assert response.status_code == 400
        assert "Invalid message_id" in response.json()["detail"]
    
    def test_send_message_empty_payload(self, client: TestClient) -> None:
        """Test send message with empty payload returns 400."""
        message_id = str(uuid4())
        timestamp = utc_now().isoformat()
        
        response = client.post(
            "/api/message/send",
            json={
                "message_id": message_id,
                "conversation_id": "conv-001",
                "payload": "",
                "timestamp": timestamp,
            },
            headers={"X-Device-ID": "sender-001"},
        )
        
        assert response.status_code == 400
        assert "payload cannot be empty" in response.json()["detail"]
    
    def test_send_message_payload_too_large(self, client: TestClient) -> None:
        """Test send message with payload exceeding 50KB returns 400."""
        message_id = str(uuid4())
        timestamp = utc_now().isoformat()
        # Create payload larger than 50KB
        large_payload = b"x" * (MAX_MESSAGE_PAYLOAD_SIZE_KB * 1024 + 1)
        payload = base64.b64encode(large_payload).decode("utf-8")
        
        response = client.post(
            "/api/message/send",
            json={
                "message_id": message_id,
                "conversation_id": "conv-001",
                "payload": payload,
                "timestamp": timestamp,
            },
            headers={"X-Device-ID": "sender-001"},
        )
        
        assert response.status_code == 400
        assert "payload size" in response.json()["detail"]
        assert "exceeds maximum" in response.json()["detail"]
    
    def test_send_message_conversation_not_active(self, client: TestClient, conversation_registry: ConversationRegistry) -> None:
        """Test send message to closed conversation returns 400."""
        # Close the conversation
        conversation_registry.close_conversation("conv-001")
        
        message_id = str(uuid4())
        timestamp = utc_now().isoformat()
        payload = base64.b64encode(b"test message").decode("utf-8")
        
        response = client.post(
            "/api/message/send",
            json={
                "message_id": message_id,
                "conversation_id": "conv-001",
                "payload": payload,
                "timestamp": timestamp,
            },
            headers={"X-Device-ID": "sender-001"},
        )
        
        assert response.status_code == 400
        assert "conversation is not active" in response.json()["detail"]
    
    def test_send_message_conversation_not_found(self, client: TestClient) -> None:
        """Test send message to non-existent conversation returns 404."""
        message_id = str(uuid4())
        timestamp = utc_now().isoformat()
        payload = base64.b64encode(b"test message").decode("utf-8")
        
        response = client.post(
            "/api/message/send",
            json={
                "message_id": message_id,
                "conversation_id": "nonexistent-conv",
                "payload": payload,
                "timestamp": timestamp,
            },
            headers={"X-Device-ID": "sender-001"},
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_send_message_derives_expiration(self, client: TestClient) -> None:
        """Test send message without expiration derives from timestamp + default expiration."""
        message_id = str(uuid4())
        timestamp = utc_now().isoformat()
        payload = base64.b64encode(b"test message").decode("utf-8")
        
        response = client.post(
            "/api/message/send",
            json={
                "message_id": message_id,
                "conversation_id": "conv-001",
                "payload": payload,
                "timestamp": timestamp,
                # No expiration provided
            },
            headers={"X-Device-ID": "sender-001"},
        )
        
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
    
    def test_send_message_logs_metadata(self, client: TestClient, logging_service: LoggingService) -> None:
        """Test send message logs metadata (no content) per Logging & Observability (#14)."""
        message_id = str(uuid4())
        timestamp = utc_now().isoformat()
        payload = base64.b64encode(b"test message").decode("utf-8")
        
        # Mock log_event to capture calls
        log_calls = []
        original_log_event = logging_service.log_event
        
        def mock_log_event(event_type: str, event_data: dict) -> None:
            log_calls.append((event_type, event_data))
            original_log_event(event_type, event_data)
        
        logging_service.log_event = mock_log_event
        
        response = client.post(
            "/api/message/send",
            json={
                "message_id": message_id,
                "conversation_id": "conv-001",
                "payload": payload,
                "timestamp": timestamp,
            },
            headers={"X-Device-ID": "sender-001"},
        )
        
        assert response.status_code == 202
        
        # Verify log event was called with metadata only (no content)
        assert len(log_calls) > 0
        event_type, event_data = log_calls[0]
        from src.shared.logging_types import LogEventType
        assert event_type == LogEventType.MESSAGE_ATTEMPTED
        assert "message_id" in event_data
        assert "conversation_id" in event_data
        assert "sender_id" in event_data
        assert "recipient_count" in event_data
        assert "message_size_bytes" in event_data
        assert "timestamp" in event_data
        # Verify no message content in logs
        assert "payload" not in event_data
        assert "content" not in event_data
