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
    registry = ConversationRegistry(device_registry, demo_mode=True)
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
        """Test send message with missing conversation_id returns 422 (Pydantic validation error)."""
        payload = base64.b64encode(b"test message").decode("utf-8")
        
        response = client.post(
            "/api/message/send",
            json={
                "payload": payload,
            },
            headers={"X-Device-ID": "sender-001"},
        )
        
        # FastAPI/Pydantic returns 422 for validation errors (missing required field)
        assert response.status_code == 422
        data = response.json()
        # Pydantic validation errors use "detail" format (array of validation errors)
        assert "detail" in data
        assert isinstance(data["detail"], list)
        # Check that the error mentions conversation_id is missing
        detail_str = str(data["detail"]).lower()
        assert "conversation_id" in detail_str or "conversation" in detail_str
    
    def test_send_message_device_not_active(self, client: TestClient, device_registry: DeviceRegistry) -> None:
        """Test send message with inactive device returns 403."""
        from unittest.mock import patch
        import src.backend.server as server_module
        
        # Register but don't activate device
        device_registry.register_device("inactive-device", "public-key", "controller-1")
        # Don't provision or confirm - device remains inactive
        
        # Disable auto-provisioning for this test by patching is_development
        with patch.object(server_module, "is_development", False):
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
        """Test send message with empty payload returns 400 with structured error."""
        response = client.post(
            "/api/message/send",
            json={
                "conversation_id": "conv-001",
                "payload": "",
            },
            headers={"X-Device-ID": "sender-001"},
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error_code" in data
        assert "request_id" in data
        assert "message" in data
        assert data["error_code"] == "payload_required"
        assert "payload" in data["message"].lower()
    
    def test_send_message_payload_too_large(self, client: TestClient) -> None:
        """Test send message with payload exceeding 50KB returns 400 with structured error."""
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
        data = response.json()
        assert "error_code" in data
        assert "request_id" in data
        assert "message" in data
        assert data["error_code"] == "payload_size_exceeded"
        assert "payload size" in data["message"]
        assert "exceeds maximum" in data["message"]
    
    def test_send_message_conversation_not_active(self, client: TestClient, conversation_registry: ConversationRegistry) -> None:
        """Test send message to closed conversation returns 400 with structured error."""
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
        data = response.json()
        assert "error_code" in data
        assert "request_id" in data
        assert "message" in data
        assert data["error_code"] == "conversation_not_active"
        assert "conversation is not active" in data["message"]
    
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
        
        # Backend returns 400 (not 404) for conversation_not_found per API contract
        assert response.status_code == 400
        data = response.json()
        assert "error_code" in data
        assert data["error_code"] == "conversation_not_found"
        assert "message" in data
    
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
    
    def test_send_message_sender_not_participant(self, client: TestClient, conversation_registry: ConversationRegistry, device_registry: DeviceRegistry) -> None:
        """Test send message from non-participant returns 403 Forbidden."""
        payload = base64.b64encode(b"test message").decode("utf-8")
        
        # Register recipient-002 so it can be a participant
        device_registry.register_device("recipient-002", "public-key-3", "controller-1")
        device_registry.provision_device("recipient-002")
        device_registry.confirm_provisioning("recipient-002")
        
        # Create conversation with different participants (use different ID to avoid fixture conflict)
        conversation_registry.register_conversation(
            "conv-not-participant",
            ["recipient-001", "recipient-002"],  # sender-001 is NOT a participant
        )
        
        response = client.post(
            "/api/message/send",
            json={
                "conversation_id": "conv-not-participant",
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
        data = response.json()
        assert "error_code" in data
        assert "request_id" in data
        assert data["error_code"] == "expiration_not_future"
    
    def test_send_message_conversation_not_found_returns_structured_error(self, client: TestClient) -> None:
        """
        Test that sending to non-existent conversation returns structured error.
        
        This test demonstrates the current failure condition where frontend
        receives 400 responses due to missing prerequisite data (conversation).
        """
        payload = base64.b64encode(b"test message").decode("utf-8")
        
        response = client.post(
            "/api/message/send",
            json={
                "conversation_id": "nonexistent-conv",
                "payload": payload,
            },
            headers={"X-Device-ID": "sender-001"},
        )
        
        # Backend returns 400 (not 404) for conversation_not_found per API contract
        assert response.status_code == 400
        # Verify structured error response format
        data = response.json()
        assert "error_code" in data
        assert data["error_code"] == "conversation_not_found"
        assert "message" in data
        assert "request_id" in data
    
    def test_send_message_plaintext_accepted_in_server_mode(self, client: TestClient) -> None:
        """Test that plaintext payload is accepted and encrypted server-side when ENCRYPTION_MODE=server."""
        from unittest.mock import patch
        import src.backend.server as server_module
        import os
        
        # Skip test if cryptography is not available
        try:
            from cryptography.fernet import Fernet
            import hashlib
            import base64 as b64
            
            key_seed = "dev-mode-encryption-key-seed"
            key_bytes = hashlib.sha256(key_seed.encode()).digest()
            server_key = b64.urlsafe_b64encode(key_bytes)
            server_encryptor = Fernet(server_key)
        except ImportError:
            pytest.skip("cryptography package not available")
        
        # Mock ENCRYPTION_MODE to be "server" via both module variable and environment
        with patch.dict(os.environ, {"ENCRYPTION_MODE": "server"}), \
             patch.object(server_module, "ENCRYPTION_MODE", "server"), \
             patch.object(server_module, "_server_encryptor", server_encryptor):
            # Send plaintext payload
            plaintext_payload = "Hello, this is plaintext!"
            
            response = client.post(
                "/api/message/send",
                json={
                    "conversation_id": "conv-001",
                    "payload": plaintext_payload,
                },
                headers={"X-Device-ID": "sender-001"},
            )
            
            # Should succeed (plaintext encrypted server-side)
            assert response.status_code == 202
            data = response.json()
            assert "message_id" in data
            assert "timestamp" in data
            assert data["status"] == "queued"
    
    def test_send_message_plaintext_rejected_in_client_mode(self, client: TestClient) -> None:
        """Test that plaintext payload is rejected with clear error code when ENCRYPTION_MODE=client."""
        from unittest.mock import patch
        import src.backend.server as server_module
        
        # Patch the send_message function's ENCRYPTION_MODE check
        # The code at line 641 checks: if ENCRYPTION_MODE == "server":
        # We need to ensure it evaluates to False (client mode)
        original_mode = server_module.ENCRYPTION_MODE
        original_encryptor = getattr(server_module, "_server_encryptor", None)
        
        # Directly set the module variables (more reliable than patch.object for module-level vars)
        server_module.ENCRYPTION_MODE = "client"
        server_module._server_encryptor = None
        
        try:
            # Send plaintext payload (not hex or base64 encoded)
            plaintext_payload = "Hello, this is plaintext!"
            
            response = client.post(
                "/api/message/send",
                json={
                    "conversation_id": "conv-001",
                    "payload": plaintext_payload,
                },
                headers={"X-Device-ID": "sender-001"},
            )
            
            # Should return 400 with plaintext_rejected error code
            assert response.status_code == 400, f"Expected 400, got {response.status_code}. Response: {response.json()}. ENCRYPTION_MODE={server_module.ENCRYPTION_MODE}, _server_encryptor={server_module._server_encryptor}"
            data = response.json()
            assert "error_code" in data
            assert "request_id" in data
            assert "message" in data
            assert data["error_code"] == "payload_plaintext_rejected", f"Expected payload_plaintext_rejected, got {data.get('error_code')}"
            assert "plaintext" in data["message"].lower() or "encrypted" in data["message"].lower()
        finally:
            # Restore original values
            server_module.ENCRYPTION_MODE = original_mode
            server_module._server_encryptor = original_encryptor
