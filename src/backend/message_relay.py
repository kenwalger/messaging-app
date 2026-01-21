"""
Backend message relay service for Abiqua Asset Management.

Implements backend relay functionality per:
- Functional Specification (#6), Section 5
- State Machines (#7), Section 3
- Data Classification & Retention (#8)
- API Contracts (#10)
- Resolved Specs & Clarifications

This module handles:
- Encrypted message relay (no plaintext storage)
- Message delivery to recipient devices
- Metadata handling (Restricted classification)
- Expiration enforcement
- WebSocket and REST delivery
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol
from uuid import UUID

from src.shared.constants import (
    API_ENDPOINT_RECEIVE_MESSAGE,
    API_ENDPOINT_SEND_MESSAGE,
    HEADER_DEVICE_ID,
    MAX_DELIVERY_RETRIES,
)
from src.shared.message_types import MessageMetadata, utc_now

# Configure logging per Logging & Observability (#14)
# Note: No message content logged per Data Classification (#8)
logger = logging.getLogger(__name__)


# Protocol definitions for abstracted services per PEP 484
class DeviceRegistry(Protocol):
    """Protocol for device registry interface."""
    
    def is_device_active(self, device_id: str) -> bool:
        """
        Check if device is active (provisioned and not revoked).
        
        Args:
            device_id: Device identifier to check.
        
        Returns:
            True if device is active, False if revoked or invalid.
        """
        ...


class WebSocketManager(Protocol):
    """Protocol for WebSocket connection manager interface."""
    
    def is_connected(self, device_id: str) -> bool:
        """
        Check if device has active WebSocket connection.
        
        Args:
            device_id: Device identifier to check.
        
        Returns:
            True if device has active WebSocket connection, False otherwise.
        """
        ...
    
    def send_to_device(self, device_id: str, message: str) -> bool:
        """
        Send message to device via WebSocket.
        
        Args:
            device_id: Target device identifier.
            message: JSON-encoded message string.
        
        Returns:
            True if message sent successfully, False otherwise.
        """
        ...


class LogService(Protocol):
    """Protocol for logging service interface."""
    
    def log_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """
        Log operational event.
        
        Args:
            event_type: Type of event (per Logging & Observability #14).
            event_data: Event data dictionary (content-free per Data Classification #8).
        """
        ...


class MessageRelayService:
    """
    Backend message relay service per Functional Spec (#6), Section 5.1.
    
    Backend acts as a relay only:
    - Never stores plaintext per Functional Spec (#6), Section 5.1
    - Does not index messages per Functional Spec (#6), Section 5.1
    - Does not retain messages beyond delivery or expiration per Functional Spec (#6), Section 5.1
    """
    
    def __init__(
        self,
        device_registry: DeviceRegistry,
        websocket_manager: Optional[WebSocketManager] = None,
        log_service: Optional[LogService] = None,
    ) -> None:
        """
        Initialize message relay service.
        
        Args:
            device_registry: Registry for validating device identities.
            websocket_manager: Optional WebSocket connection manager for real-time delivery.
            log_service: Optional logging service for operational events per
                Logging & Observability (#14).
        """
        self.device_registry = device_registry
        self.websocket_manager = websocket_manager
        self.log_service = log_service
        
        # Temporary message storage for delivery per Functional Spec (#6), Section 5.1
        # Classification: Restricted (metadata only) per Data Classification (#8)
        # Delete immediately after delivery per Data Classification (#8), Section 4
        self._pending_deliveries: Dict[UUID, Dict[str, Any]] = {}  # message_id -> delivery metadata
    
    def relay_message(
        self,
        sender_id: str,
        recipients: List[str],
        encrypted_payload: bytes,
        message_id: UUID,
        expiration_timestamp: datetime,
        conversation_id: str,
    ) -> bool:
        """
        Relay encrypted message to recipients per API Contracts (#10), Section 3.3.
        
        Backend never stores plaintext per Functional Spec (#6), Section 5.1.
        Metadata is Restricted classification per Data Classification (#8), Section 3.
        
        Args:
            sender_id: Sender device ID
            recipients: List of recipient device IDs
            encrypted_payload: Encrypted message payload (never decrypted)
            message_id: Message UUID (client-generated per Resolved Clarifications)
            expiration_timestamp: Message expiration time
            conversation_id: Conversation identifier
        
        Returns:
            True if message queued for delivery, False if expired or invalid
        """
        # Validate sender identity per API Contracts (#10), Section 5
        if not self.device_registry.is_device_active(sender_id):
            logger.warning(f"Invalid or revoked sender device: {sender_id}")
            return False
        
        # Check if message already expired per API Contracts (#10), Section 5
        if utc_now() >= expiration_timestamp:
            logger.debug(f"Message {message_id} expired, rejecting")
            return False
        
        # Validate recipients per Resolved TBDs (max 50 per conversation)
        if len(recipients) > 50:
            logger.warning(f"Recipients exceed max group size: {len(recipients)}")
            return False
        
        # Validate recipient devices per API Contracts (#10), Section 5
        valid_recipients = [
            rid for rid in recipients
            if self.device_registry.is_device_active(rid)
        ]
        
        if not valid_recipients:
            logger.warning(f"No valid recipients for message {message_id}")
            return False
        
        # Store delivery metadata temporarily per Functional Spec (#6), Section 5.1
        # Classification: Restricted per Data Classification (#8), Section 3
        delivery_metadata = {
            "message_id": message_id,
            "sender_id": sender_id,
            "recipients": valid_recipients,
            "encrypted_payload": encrypted_payload,
            "expiration_timestamp": expiration_timestamp,
            "conversation_id": conversation_id,
            "created_at": utc_now(),
        }
        
        self._pending_deliveries[message_id] = delivery_metadata
        
        # Attempt delivery to all valid recipients
        delivery_success = False
        for recipient_id in valid_recipients:
            if self._deliver_to_recipient(recipient_id, delivery_metadata):
                delivery_success = True
        
        # Clean up metadata after delivery attempt per Data Classification (#8), Section 4
        # Note: Metadata deleted immediately after delivery per Data Classification (#8)
        if delivery_success:
            # Keep metadata temporarily for retry if needed
            # Will be cleaned up by expiration cleanup
            pass
        
        return delivery_success
    
    def _deliver_to_recipient(
        self,
        recipient_id: str,
        delivery_metadata: Dict[str, Any],
    ) -> bool:
        """
        Deliver message to specific recipient per API Contracts (#10).
        
        Prefers WebSocket delivery, falls back to queueing for REST polling.
        
        Args:
            recipient_id: Recipient device ID
            delivery_metadata: Message delivery metadata
        
        Returns:
            True if delivered or queued, False if failed
        """
        # Attempt WebSocket delivery (preferred) per Resolved TBDs
        if self.websocket_manager and self.websocket_manager.is_connected(recipient_id):
            try:
                return self._deliver_via_websocket(recipient_id, delivery_metadata)
            except Exception as e:
                logger.warning(f"WebSocket delivery failed for {recipient_id}: {e}")
        
        # Message will be available via REST polling per API Contracts (#10), Section 3.4
        # Backend queues message for REST retrieval
        return True  # Queued for REST polling
    
    def _deliver_via_websocket(
        self,
        recipient_id: str,
        delivery_metadata: Dict[str, Any],
    ) -> bool:
        """
        Deliver message via WebSocket per Resolved Clarifications.
        
        Message format: JSON {id, conversation_id, payload, timestamp}
        
        Args:
            recipient_id: Target recipient device identifier.
            delivery_metadata: Message delivery metadata dictionary.
        
        Returns:
            True if message sent successfully, False otherwise.
        """
        if not self.websocket_manager:
            return False
        
        # Prepare WebSocket message per Resolved Clarifications
        ws_message = {
            "id": str(delivery_metadata["message_id"]),
            "conversation_id": delivery_metadata["conversation_id"],
            "payload": delivery_metadata["encrypted_payload"].hex(),  # Hex-encoded
            "timestamp": delivery_metadata["created_at"].isoformat(),
            "sender_id": delivery_metadata["sender_id"],
            "expiration": delivery_metadata["expiration_timestamp"].isoformat(),
        }
        
        # Send via WebSocket
        # Note: WebSocketManager.send_to_device() is sync for Protocol compatibility
        # Actual async sending should be handled by the WebSocket manager implementation
        # For now, we'll use the sync method (FastAPIWebSocketManager will handle async internally)
        return self.websocket_manager.send_to_device(recipient_id, json.dumps(ws_message))
    
    def get_pending_messages(
        self,
        device_id: str,
        last_received_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get pending messages for device via REST polling per API Contracts (#10), Section 3.4.
        
        Endpoint: GET /api/message/receive
        
        Returns only messages not yet expired per API Contracts (#10), Section 5.
        
        Args:
            device_id: Device ID requesting messages
            last_received_id: Last received message ID (for pagination)
        
        Returns:
            List of message dictionaries with encrypted payloads. Each dictionary contains:
            - message_id: Message UUID as string
            - payload: Hex-encoded encrypted payload
            - sender_id: Sender device identifier
            - expiration: Expiration timestamp as ISO string
            - conversation_id: Conversation identifier
        """
        # Validate device identity per API Contracts (#10), Section 5
        if not self.device_registry.is_device_active(device_id):
            logger.warning(f"Invalid or revoked device requesting messages: {device_id}")
            return []
        
        current_time = utc_now()
        pending_messages = []
        
        # Find messages for this device
        for message_id, metadata in self._pending_deliveries.items():
            # Check if expired per API Contracts (#10), Section 5
            if current_time >= metadata["expiration_timestamp"]:
                continue  # Skip expired messages
            
            # Check if for this recipient
            if device_id not in metadata["recipients"]:
                continue
            
            # Check if already received (using last_received_id for pagination)
            if last_received_id and message_id <= last_received_id:
                continue
            
            # Prepare message response per API Contracts (#10), Section 3.4
            message_response = {
                "message_id": str(message_id),
                "payload": metadata["encrypted_payload"].hex(),  # Hex-encoded
                "sender_id": metadata["sender_id"],
                "expiration": metadata["expiration_timestamp"].isoformat(),
                "conversation_id": metadata["conversation_id"],
            }
            
            pending_messages.append(message_response)
        
        return pending_messages
    
    def cleanup_expired_messages(self) -> None:
        """
        Cleanup expired messages per Data Classification (#8), Section 4.
        
        Metadata deleted immediately after expiration per Data Classification (#8).
        Backend does not retain messages beyond expiration per Functional Spec (#6), Section 5.1.
        
        Note:
            Removes all expired messages from pending deliveries.
        """
        current_time = utc_now()
        
        expired_message_ids = [
            msg_id
            for msg_id, metadata in self._pending_deliveries.items()
            if current_time >= metadata["expiration_timestamp"]
        ]
        
        for msg_id in expired_message_ids:
            # Delete metadata immediately per Data Classification (#8), Section 4
            self._pending_deliveries.pop(msg_id, None)
            logger.debug(f"Cleaned up expired message {msg_id}")
    
    def acknowledge_delivery(
        self,
        message_id: UUID,
        device_id: str,
    ) -> bool:
        """
        Acknowledge message delivery per Resolved Clarifications.
        
        WebSocket delivery acknowledgment per message ID.
        
        Args:
            message_id: Message UUID
            device_id: Device ID acknowledging delivery
        
        Returns:
            True if acknowledgment processed
        """
        if message_id in self._pending_deliveries:
            metadata = self._pending_deliveries[message_id]
            
            # Remove device from recipients list (delivered)
            if device_id in metadata["recipients"]:
                metadata["recipients"].remove(device_id)
            
            # Clean up if all recipients delivered
            if not metadata["recipients"]:
                self._pending_deliveries.pop(message_id, None)
                logger.debug(f"All recipients delivered message {message_id}")
            
            return True
        
        return False
