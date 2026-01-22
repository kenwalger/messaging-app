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
        """Test successful message send returns 202 Accepted with server-assigned message_id."""
        expiration = (utc_now() + timedelta(days=7)).isoformat()
        payload = base64.b64encode(b"test message payload").decode("utf-8")
        
        response = client.post(
            "/api/message/send",
            json={
                "conversation_id": "conv-001",
                "payload": payload,
                "expiration": expiration,
            },
            headers={"X-Device-ID": "sender-001"},
        )
        
        assert response.status_code == 202
        data = response.json()
        assert "message_id" in data
        assert "timestamp" in data
        assert data["status"] == "queued"
        # Verify message_id is a valid UUID
        from uuid import UUID
        UUID(data["message_id"])  # Will raise ValueError if invalid
    
    def test_send_message_missing_conversation_id(self, client: TestClient) -> None:
        """Test send message with missing conversation_id returns 400."""
        payload = base64.b64encode(b"test message").decode("utf-8")
        
        response = client.post(
            "/api/message/send",
            json={
                "payload": payload,
            },
            headers={"X-Device-ID": "sender-001"},
        )
        
        assert response.status_code == 400
        assert "conversation_id is required" in response.json()["detail"]
    
    def test_send_message_device_not_active(self, client: TestClient, device_registry: DeviceRegistry) -> None:
        """Test send message with inactive device returns 403."""
        # Register but don't activate device
        device_registry.register_device("inactive-device", "public-key", "controller-1")
        # Don't provision or confirm - device remains inactive
        
        payload = base64.b64encode(b"test message").decode("utf-8")
        
        response = client.post(
            "/api/message/send",
            json={
                "conversation_id": "conv-001",
                "payload": payload,
            },
            headers={"X-Device-ID": "inactive-device"},
        )
        
        assert response.status_code == 403
        assert "not active" in response.json()["detail"].lower()
    
    def test_send_message_empty_payload(self, client: TestClient) -> None:
        """Test send message with empty payload returns 400."""
        response = client.post(
            "/api/message/send",
            json={
                "conversation_id": "conv-001",
                "payload": "",
            },
            headers={"X-Device-ID": "sender-001"},
        )
        
        assert response.status_code == 400
        assert "payload" in response.json()["detail"].lower()
    
    def test_send_message_payload_too_large(self, client: TestClient) -> None:
        """Test send message with payload exceeding 50KB returns 400."""
        # Create payload larger than 50KB
        large_payload = b"x" * (MAX_MESSAGE_PAYLOAD_SIZE_KB * 1024 + 1)
        payload = base64.b64encode(large_payload).decode("utf-8")
        
        response = client.post(
            "/api/message/send",
            json={
                "conversation_id": "conv-001",
                "payload": payload,
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
        
        payload = base64.b64encode(b"test message").decode("utf-8")
        
        response = client.post(
            "/api/message/send",
            json={
                "conversation_id": "conv-001",
                "payload": payload,
            },
            headers={"X-Device-ID": "sender-001"},
        )
        
        assert response.status_code == 400
        assert "conversation is not active" in response.json()["detail"]
    
    def test_send_message_conversation_not_found(self, client: TestClient) -> None:
        """Test send message to non-existent conversation returns 404."""
        payload = base64.b64encode(b"test message").decode("utf-8")
        
        response = client.post(
            "/api/message/send",
            json={
                "conversation_id": "nonexistent-conv",
                "payload": payload,
            },
            headers={"X-Device-ID": "sender-001"},
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_send_message_derives_expiration(self, client: TestClient) -> None:
        """Test send message without expiration derives from server timestamp + default expiration."""
        payload = base64.b64encode(b"test message").decode("utf-8")
        
        response = client.post(
            "/api/message/send",
            json={
                "conversation_id": "conv-001",
                "payload": payload,
                # No expiration provided
            },
            headers={"X-Device-ID": "sender-001"},
        )
        
        assert response.status_code == 202
        data = response.json()
        assert "message_id" in data
        assert "timestamp" in data
        assert data["status"] == "queued"
    
    def test_send_message_logs_metadata(self, client: TestClient, logging_service: LoggingService) -> None:
        """Test send message logs metadata (no content) per Logging & Observability (#14)."""
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
                "conversation_id": "conv-001",
                "payload": payload,
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
    
    def test_send_message_sender_not_participant(self, client: TestClient, conversation_registry: ConversationRegistry) -> None:
        """Test send message from non-participant returns 403 Forbidden."""
        payload = base64.b64encode(b"test message").decode("utf-8")
        
        # Create conversation with different participants
        conversation_registry.register_conversation(
            "conv-001",
            ["recipient-001", "recipient-002"],  # sender-001 is NOT a participant
        )
        
        response = client.post(
            "/api/message/send",
            json={
                "conversation_id": "conv-001",
                "payload": payload,
            },
            headers={"X-Device-ID": "sender-001"},  # sender-001 is not a participant
        )
        
        assert response.status_code == 403
        assert "not a participant" in response.json()["detail"].lower()
    
    def test_send_message_invalid_expiration(self, client: TestClient) -> None:
        """Test send message with invalid expiration (past timestamp) returns 400."""
        payload = base64.b64encode(b"test message").decode("utf-8")
        # Expiration in the past
        past_expiration = (utc_now() - timedelta(days=1)).isoformat()
        
        response = client.post(
            "/api/message/send",
            json={
                "conversation_id": "conv-001",
                "payload": payload,
                "expiration": past_expiration,
            },
            headers={"X-Device-ID": "sender-001"},
        )
        
        assert response.status_code == 400
        assert "expiration" in response.json()["detail"].lower()
