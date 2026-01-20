"""
Client-side message delivery module for Abiqua Asset Management.

Implements message creation, delivery, expiration, and offline queuing per:
- Functional Specification (#6), Sections 4.2-4.5, 10
- State Machines (#7), Section 3
- Data Classification & Retention (#8)
- Lifecycle Playbooks (#15), Section 5
- Resolved Specs & Clarifications

This module handles:
- Message creation and encryption
- Message queuing for offline delivery
- WebSocket and REST delivery mechanisms
- Message expiration enforcement
- Duplicate message detection
- Retry logic with limits
"""

import hashlib
import json
import logging
import math
import time
from datetime import datetime, timedelta
from queue import Queue
from threading import Event, Lock, Thread, Timer
from typing import Any, Callable, Dict, List, Optional, Protocol, Set
from uuid import UUID, uuid4

from src.shared.constants import (
    ACK_TIMEOUT_SECONDS,
    API_ENDPOINT_RECEIVE_MESSAGE,
    DEFAULT_MESSAGE_EXPIRATION_DAYS,
    ERROR_BACKEND_UNREACHABLE,
    ERROR_NETWORK_UNAVAILABLE,
    HEADER_DEVICE_ID,
    LOG_EVENT_DELIVERY_FAILED,
    LOG_EVENT_MESSAGE_ATTEMPTED,
    MAX_BACKOFF_SECONDS,
    MAX_DELIVERY_RETRIES,
    MAX_OFFLINE_MESSAGES,
    MAX_OFFLINE_STORAGE_MB,
    REST_POLLING_INTERVAL_SECONDS,
    RETRY_BACKOFF_BASE_SECONDS,
    WEBSOCKET_RECONNECT_TIMEOUT_SECONDS,
)
from src.shared.message_types import (
    DeliveryAcknowledgment,
    Message,
    MessageState,
    QueuedMessage,
    utc_now,
)

# Configure logging per Logging & Observability (#14)
# Note: No message content logged per Data Classification (#8)
logger = logging.getLogger(__name__)


# Protocol definitions for abstracted services per PEP 484
class EncryptionService(Protocol):
    """Protocol for encryption service interface."""
    
    def encrypt(self, plaintext: bytes) -> bytes:
        """
        Encrypt plaintext message content.
        
        Args:
            plaintext: Plaintext message content to encrypt.
        
        Returns:
            Encrypted message payload as bytes.
        """
        ...
    
    def decrypt(self, encrypted_payload: bytes) -> bytes:
        """
        Decrypt encrypted message payload.
        
        Args:
            encrypted_payload: Encrypted message payload to decrypt.
        
        Returns:
            Decrypted plaintext message content as bytes.
        
        Raises:
            Exception: If decryption fails.
        """
        ...


class StorageService(Protocol):
    """Protocol for secure storage service interface."""
    
    def store_message(self, message_id: UUID, encrypted_payload: bytes) -> None:
        """
        Store encrypted message at rest.
        
        Args:
            message_id: Message UUID identifier.
            encrypted_payload: Encrypted message payload to store.
        """
        ...
    
    def delete_message(self, message_id: UUID) -> None:
        """
        Delete message from storage.
        
        Args:
            message_id: Message UUID identifier to delete.
        """
        ...


class WebSocketClient(Protocol):
    """Protocol for WebSocket client interface."""
    
    def send(self, message: str) -> None:
        """
        Send message via WebSocket.
        
        Args:
            message: JSON-encoded message string to send.
        """
        ...


class HttpClient(Protocol):
    """Protocol for HTTP client interface."""
    
    def post(
        self,
        url: str,
        json: Dict[str, Any],
        headers: Dict[str, str],
    ) -> Any:
        """
        Send POST request via HTTP.
        
        Args:
            url: API endpoint URL.
            json: Request body as dictionary.
            headers: HTTP headers as dictionary.
        
        Returns:
            Response object with status_code and json() method.
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


class MessageDeliveryService:
    """
    Message delivery service per Functional Spec (#6) and State Machines (#7).
    
    Handles complete message lifecycle from creation to expiration.
    """
    
    def __init__(
        self,
        device_id: str,
        encryption_service: EncryptionService,
        storage_service: StorageService,
        websocket_client: Optional[WebSocketClient] = None,
        http_client: Optional[HttpClient] = None,
        log_service: Optional[LogService] = None,
    ) -> None:
        """
        Initialize message delivery service.
        
        Args:
            device_id: Device-bound identity per Identity Provisioning (#11).
            encryption_service: Service for encrypting/decrypting messages.
            storage_service: Secure storage for encrypted messages at rest.
            websocket_client: Optional WebSocket client (preferred) per Resolved TBDs.
            http_client: Optional HTTP client for REST fallback per Resolved TBDs.
            log_service: Optional logging service for operational events per
                Logging & Observability (#14).
        """
        self.device_id = device_id
        self.encryption_service = encryption_service
        self.storage_service = storage_service
        self.websocket_client = websocket_client
        self.http_client = http_client
        self.log_service = log_service
        
        # Offline message queue per Functional Spec (#6), Section 10
        self._offline_queue: Queue = Queue()
        self._queue_lock = Lock()
        self._queued_messages: Dict[UUID, QueuedMessage] = {}
        self._queued_storage_size = 0  # Track storage size in bytes
        
        # Received messages tracking for duplicate detection per Resolved Clarifications
        self._received_message_ids: Set[UUID] = set()
        self._received_content_hashes: Set[str] = set()
        
        # Expiration timers per State Machines (#7), Section 7
        self._expiration_timers: Dict[UUID, Timer] = {}
        self._timer_lock = Lock()
        
        # Message state tracking per State Machines (#7)
        self._messages: Dict[UUID, Message] = {}
        
        # WebSocket connection state per Resolved Clarifications
        self._websocket_connected = False
        self._websocket_reconnect_attempts = 0
        self._websocket_reconnect_timer: Optional[Timer] = None
        self._rest_polling_active = False
        self._rest_polling_thread: Optional[Thread] = None
        self._rest_polling_stop_event = Event()
        
        # ACK tracking per Resolved Clarifications (#51)
        # Track pending ACKs for WebSocket messages
        self._pending_acks: Dict[UUID, datetime] = {}  # message_id -> sent_at timestamp
        self._ack_lock = Lock()
        
        # Exponential backoff state for retries per Lifecycle Playbooks (#15)
        self._retry_backoff_base = RETRY_BACKOFF_BASE_SECONDS
        self._max_backoff = MAX_BACKOFF_SECONDS
    
    def create_message(
        self,
        plaintext_content: bytes,
        recipients: List[str],
        conversation_id: str,
        expiration_days: int = DEFAULT_MESSAGE_EXPIRATION_DAYS,
    ) -> Message:
        """
        Create a new message per Functional Spec (#6), Section 4.2.
        
        Message is encrypted on device before transmission.
        No plaintext leaves the device per Functional Spec (#6), Section 4.2.
        
        Args:
            plaintext_content: Plaintext message content (max 50KB per Resolved TBDs)
            recipients: List of recipient device IDs (max 50 per Resolved TBDs)
            conversation_id: Conversation identifier
            expiration_days: Expiration period in days (default 7 per Resolved TBDs)
        
        Returns:
            Message object in CREATED state per State Machines (#7)
        
        Raises:
            ValueError: If constraints violated (group size, payload size)
        """
        # Validate constraints per Resolved TBDs
        if len(recipients) > 50:  # MAX_GROUP_SIZE
            raise ValueError("Recipients exceed max group size of 50")
        
        if len(plaintext_content) > 50 * 1024:  # MAX_MESSAGE_PAYLOAD_SIZE_KB
            raise ValueError("Payload exceeds max size of 50KB")
        
        # Generate UUID v4 message ID per Resolved Clarifications
        message_id = uuid4()
        
        # Encrypt payload on device per Functional Spec (#6), Section 4.2
        encrypted_payload = self.encryption_service.encrypt(plaintext_content)
        
        # Create timestamps per Functional Spec (#6), Section 4.2
        creation_timestamp = utc_now()
        expiration_timestamp = creation_timestamp + timedelta(days=expiration_days)
        
        # Create message in CREATED state per State Machines (#7), Section 3
        message = Message(
            message_id=message_id,
            sender_id=self.device_id,
            recipients=recipients,
            payload=encrypted_payload,
            conversation_id=conversation_id,
            creation_timestamp=creation_timestamp,
            expiration_timestamp=expiration_timestamp,
            state=MessageState.CREATED,
            retry_count=0,
        )
        
        # Store message per State Machines (#7)
        self._messages[message_id] = message
        
        # Log message attempt (no content) per Logging & Observability (#14), Section 3
        if self.log_service:
            self.log_service.log_event(
                LOG_EVENT_MESSAGE_ATTEMPTED,
                {
                    "message_id": str(message_id),
                    "sender_id": self.device_id,
                    "recipient_count": len(recipients),
                    "timestamp": creation_timestamp.isoformat(),
                },
            )
        
        return message
    
    def send_message(self, message: Message) -> bool:
        """
        Send message via WebSocket or REST per API Contracts (#10) and Resolved TBDs.
        
        Transitions: CREATED -> PENDING_DELIVERY per State Machines (#7), Section 3.
        
        Args:
            message: Message in CREATED state
        
        Returns:
            True if queued for delivery, False if queued offline
        """
        # Transition to PENDING_DELIVERY per State Machines (#7), Section 3
        message.state = MessageState.PENDING_DELIVERY
        self._messages[message.message_id] = message
        
        # Attempt WebSocket delivery (preferred) per Resolved TBDs
        if self._websocket_connected and self.websocket_client:
            try:
                return self._send_via_websocket(message)
            except Exception as e:
                logger.warning(f"WebSocket send failed: {e}, falling back to REST")
        
        # Fallback to REST or queue offline per Functional Spec (#6), Section 10
        if self.http_client:
            try:
                return self._send_via_rest(message)
            except Exception as e:
                logger.warning(f"REST send failed: {e}, queueing offline")
        
        # Queue for offline delivery per Functional Spec (#6), Section 10
        self._queue_message_offline(message)
        return False
    
    def _send_via_websocket(self, message: Message) -> bool:
        """
        Send message via WebSocket per Resolved Clarifications.
        
        Message format: JSON {id, conversation_id, payload, timestamp}
        Authentication: X-Device-ID header + ephemeral session token
        
        Args:
            message: Message to send via WebSocket.
        
        Returns:
            True if message sent successfully, False otherwise.
        
        Raises:
            Exception: If WebSocket send fails (caught and logged by caller).
        """
        if not self.websocket_client:
            return False
        
        # Prepare WebSocket message per Resolved Clarifications
        ws_message = {
            "id": str(message.message_id),
            "conversation_id": message.conversation_id,
            "payload": message.payload.hex(),  # Hex-encoded encrypted payload
            "timestamp": message.creation_timestamp.isoformat(),
            "sender_id": message.sender_id,
            "recipients": message.recipients,
            "expiration": message.expiration_timestamp.isoformat(),
        }
        
        # Send via WebSocket
        self.websocket_client.send(json.dumps(ws_message))
        
        # Track pending ACK per Resolved Clarifications (#51)
        with self._ack_lock:
            self._pending_acks[message.message_id] = utc_now()
        
        # Start ACK timeout timer per Resolved Clarifications
        ack_timer = Timer(
            ACK_TIMEOUT_SECONDS,
            self._handle_ack_timeout,
            args=(message.message_id,),
        )
        ack_timer.daemon = True
        ack_timer.start()
        
        return True
    
    def _send_via_rest(self, message: Message) -> bool:
        """
        Send message via REST API per API Contracts (#10), Section 3.3.
        
        Endpoint: POST /api/message/send
        Headers: X-Device-ID
        
        Args:
            message: Message to send via REST API.
        
        Returns:
            True if message sent successfully (HTTP 200), False otherwise.
        
        Raises:
            Exception: If REST request fails (caught and logged by caller).
        """
        if not self.http_client:
            return False
        
        # Prepare REST request per API Contracts (#10), Section 3.3
        request_data = {
            "sender_id": message.sender_id,
            "recipients": message.recipients,
            "payload": message.payload.hex(),  # Hex-encoded encrypted payload
            "expiration": message.expiration_timestamp.isoformat(),
        }
        
        headers = {HEADER_DEVICE_ID: self.device_id}
        
        # Send via REST
        response = self.http_client.post(
            "/api/message/send",
            json=request_data,
            headers=headers,
        )
        
        if response.status_code == 200:
            response_data = response.json()
            # Update message ID if server assigned one (should match client UUID)
            if "message_id" in response_data:
                # Validate server message_id matches client-generated UUID
                server_message_id = UUID(response_data["message_id"])
                if server_message_id != message.message_id:
                    logger.warning("Server message_id mismatch, using client UUID")
            return True
        
        return False
    
    def _queue_message_offline(self, message: Message) -> None:
        """
        Queue message for offline delivery per Functional Spec (#6), Section 10.
        
        Enforces storage limits per Resolved TBDs:
        - Max 500 messages or 50MB
        - Eviction only for expired messages per Resolved Clarifications
        
        Args:
            message: Message to queue for offline delivery.
        
        Note:
            Message state may be set to FAILED if queue is full and no expired
            messages can be evicted.
        """
        with self._queue_lock:
            # Check if message already expired per Resolved Clarifications
            if message.is_expired():
                logger.debug(f"Message {message.message_id} expired, not queuing")
                return
            
            # Enforce storage limits per Resolved TBDs
            self._enforce_offline_storage_limits()
            
            # Check if we can queue this message
            message_size = len(message.payload)
            if (
                len(self._queued_messages) >= MAX_OFFLINE_MESSAGES
                or (self._queued_storage_size + message_size) > (MAX_OFFLINE_STORAGE_MB * 1024 * 1024)
            ):
                # Only evict expired messages per Resolved Clarifications
                if not self._evict_expired_messages():
                    # Cannot queue: storage full and no expired messages to evict
                    logger.warning("Offline queue full, cannot queue message")
                    message.state = MessageState.FAILED
                    return
            
            # Queue message
            queued = QueuedMessage(
                message=message,
                queued_at=utc_now(),
            )
            self._queued_messages[message.message_id] = queued
            self._queued_storage_size += message_size
    
    def _enforce_offline_storage_limits(self) -> None:
        """
        Enforce offline storage limits per Resolved TBDs and Clarifications.
        
        Eviction applies only to expired messages per Resolved Clarifications.
        Oldest expired messages removed first.
        
        Note:
            Logs warnings if limits are still exceeded after eviction.
        """
        # Remove expired messages from queue per Resolved Clarifications
        self._evict_expired_messages()
        
        # Check if still over limits (should not happen if eviction worked)
        if len(self._queued_messages) > MAX_OFFLINE_MESSAGES:
            logger.warning("Offline queue exceeds message count limit after eviction")
        
        current_size_mb = self._queued_storage_size / (1024 * 1024)
        if current_size_mb > MAX_OFFLINE_STORAGE_MB:
            logger.warning("Offline queue exceeds storage size limit after eviction")
    
    def _evict_expired_messages(self) -> bool:
        """
        Evict expired messages from offline queue per Resolved Clarifications.
        
        Returns:
            True if any messages were evicted, False otherwise
        """
        current_time = utc_now()
        evicted = False
        
        # Find expired messages (oldest first)
        expired_messages = [
            (msg_id, queued)
            for msg_id, queued in self._queued_messages.items()
            if queued.message.is_expired(current_time)
        ]
        expired_messages.sort(key=lambda x: x[1].queued_at)
        
        # Remove expired messages
        for msg_id, queued in expired_messages:
            self._queued_messages.pop(msg_id, None)
            self._queued_storage_size -= len(queued.message.payload)
            queued.message.state = MessageState.EXPIRED
            evicted = True
            logger.debug(f"Evicted expired message {msg_id} from offline queue")
        
        return evicted
    
    def receive_message(
        self,
        message_id: UUID,
        encrypted_payload: bytes,
        sender_id: str,
        conversation_id: str,
        expiration_timestamp: datetime,
    ) -> Optional[Message]:
        """
        Receive and process incoming message per Functional Spec (#6), Section 4.3.
        
        Transitions: DELIVERED -> ACTIVE per State Machines (#7), Section 3.
        
        Performs duplicate detection per Resolved Clarifications:
        - Primary: Message ID comparison
        - Secondary: Content hash comparison
        
        Args:
            message_id: Message UUID
            encrypted_payload: Encrypted message payload
            sender_id: Sender device ID
            conversation_id: Conversation identifier
            expiration_timestamp: Message expiration time
        
        Returns:
            Message object if successfully received, None if duplicate or expired.
        
        Raises:
            Exception: If decryption fails (caught and logged, returns None).
        """
        # Check if expired per Functional Spec (#6), Section 4.4
        if utc_now() >= expiration_timestamp:
            logger.debug(f"Message {message_id} expired, not processing")
            return None
        
        # Duplicate detection: Message ID first per Resolved Clarifications
        if message_id in self._received_message_ids:
            logger.debug(f"Duplicate message ID {message_id}, discarding")
            return None
        
        # Duplicate detection: Content hash secondary per Resolved Clarifications
        content_hash = hashlib.sha256(encrypted_payload).hexdigest()
        if content_hash in self._received_content_hashes:
            logger.debug(f"Duplicate content hash for message {message_id}, discarding")
            return None
        
        # Decrypt payload locally per Functional Spec (#6), Section 4.3
        try:
            plaintext = self.encryption_service.decrypt(encrypted_payload)
        except Exception as e:
            logger.error(f"Failed to decrypt message {message_id}: {e}")
            return None
        
        # Create message in DELIVERED state per State Machines (#7), Section 3
        message = Message(
            message_id=message_id,
            sender_id=sender_id,
            recipients=[self.device_id],  # This device is the recipient
            payload=encrypted_payload,  # Store encrypted at rest per Data Classification (#8)
            conversation_id=conversation_id,
            creation_timestamp=utc_now(),  # Local timestamp per Functional Spec (#6)
            expiration_timestamp=expiration_timestamp,
            state=MessageState.DELIVERED,
            retry_count=0,
        )
        
        # Store encrypted at rest per Functional Spec (#6), Section 4.3
        self.storage_service.store_message(message_id, encrypted_payload)
        
        # Transition to ACTIVE state per State Machines (#7), Section 3
        message.state = MessageState.ACTIVE
        self._messages[message_id] = message
        
        # Track for duplicate detection
        self._received_message_ids.add(message_id)
        self._received_content_hashes.add(content_hash)
        
        # Start expiration timer per State Machines (#7), Section 7
        self._start_expiration_timer(message)
        
        return message
    
    def _start_expiration_timer(self, message: Message) -> None:
        """
        Start expiration timer per State Machines (#7), Section 7.
        
        Timer enforcement is device-local per State Machines (#7), Section 7.
        
        Args:
            message: Message to start expiration timer for.
        
        Note:
            If message is already expired, it will be deleted immediately.
        """
        with self._timer_lock:
            # Cancel existing timer if any
            if message.message_id in self._expiration_timers:
                self._expiration_timers[message.message_id].cancel()
            
            # Calculate delay until expiration
            delay_seconds = (message.expiration_timestamp - utc_now()).total_seconds()
            
            if delay_seconds <= 0:
                # Already expired, delete immediately
                self._expire_message(message.message_id)
                return
            
            # Create timer (daemon thread to allow process exit)
            timer = Timer(delay_seconds, self._expire_message, args=(message.message_id,))
            timer.daemon = True  # Ensure timer doesn't prevent process exit
            timer.start()
            self._expiration_timers[message.message_id] = timer
    
    def _expire_message(self, message_id: UUID) -> None:
        """
        Expire message per Functional Spec (#6), Section 4.4 and State Machines (#7), Section 3.
        
        Actions:
        - Delete from device storage
        - Remove from UI (handled by UI layer)
        - Mark as EXPIRED state
        
        Expired messages are irrecoverable per Functional Spec (#6), Section 4.4.
        
        Args:
            message_id: UUID of message to expire.
        
        Note:
            If message is not found, method returns silently.
        """
        with self._timer_lock:
            # Remove timer
            self._expiration_timers.pop(message_id, None)
        
        # Get message
        message = self._messages.get(message_id)
        if not message:
            return
        
        # Transition to EXPIRED state per State Machines (#7), Section 3
        message.state = MessageState.EXPIRED
        
        # Delete from device storage per Functional Spec (#6), Section 4.4
        self.storage_service.delete_message(message_id)
        
        # Remove from tracking
        self._messages.pop(message_id, None)
        self._received_message_ids.discard(message_id)
        
        # Remove from offline queue if present
        with self._queue_lock:
            queued = self._queued_messages.pop(message_id, None)
            if queued:
                self._queued_storage_size -= len(queued.message.payload)
        
        logger.debug(f"Message {message_id} expired and deleted")
    
    def handle_delivery_ack(self, message_id: UUID) -> None:
        """
        Handle delivery acknowledgment per Resolved Clarifications (#51).
        
        ACK per message ID to ensure deterministic delivery.
        Transitions message from PENDING_DELIVERY to DELIVERED per State Machines (#7), Section 3.
        
        Args:
            message_id: UUID of message that was acknowledged.
        """
        with self._ack_lock:
            if message_id not in self._pending_acks:
                logger.debug(f"ACK received for unknown message {message_id}")
                return
            
            # Remove from pending ACKs
            self._pending_acks.pop(message_id, None)
        
        # Update message state to DELIVERED per State Machines (#7), Section 3
        message = self._messages.get(message_id)
        if message and message.state == MessageState.PENDING_DELIVERY:
            message.state = MessageState.DELIVERED
            logger.debug(f"Message {message_id} acknowledged and delivered")
    
    def _handle_ack_timeout(self, message_id: UUID) -> None:
        """
        Handle ACK timeout per Resolved Clarifications (#51).
        
        If ACK not received within timeout, retry delivery with exponential backoff.
        
        Args:
            message_id: UUID of message that timed out waiting for ACK.
        """
        with self._ack_lock:
            if message_id not in self._pending_acks:
                return  # ACK already received or message removed
            
            # ACK timeout - remove from pending and retry
            self._pending_acks.pop(message_id, None)
        
        message = self._messages.get(message_id)
        if not message:
            return
        
        # Check if message expired - don't retry expired messages per Functional Spec (#6), Section 4.4
        if message.is_expired():
            message.state = MessageState.EXPIRED
            logger.debug(f"Message {message_id} expired while waiting for ACK")
            return
        
        # Retry delivery with exponential backoff per Lifecycle Playbooks (#15)
        if message.retry_count < MAX_DELIVERY_RETRIES:
            logger.debug(f"ACK timeout for message {message_id}, retrying")
            self._retry_message_with_backoff(message)
        else:
            # Max retries exceeded - mark as failed per Lifecycle Playbooks (#15)
            message.state = MessageState.FAILED
            if self.log_service:
                self.log_service.log_event(
                    LOG_EVENT_DELIVERY_FAILED,
                    {
                        "message_id": str(message_id),
                        "device_id": self.device_id,
                        "retry_count": message.retry_count,
                        "timestamp": utc_now().isoformat(),
                    },
                )
            logger.warning(f"Message {message_id} failed after max retries")
    
    def _calculate_backoff_delay(self, retry_count: int) -> float:
        """
        Calculate exponential backoff delay per Lifecycle Playbooks (#15).
        
        Formula: min(base * 2^retry_count, max_backoff)
        
        Args:
            retry_count: Current retry attempt number (0-based).
        
        Returns:
            Backoff delay in seconds.
        """
        delay = self._retry_backoff_base * (2 ** retry_count)
        return min(delay, self._max_backoff)
    
    def _retry_message_with_backoff(self, message: Message) -> None:
        """
        Retry message delivery with exponential backoff per Lifecycle Playbooks (#15).
        
        Args:
            message: Message to retry.
        """
        # Calculate backoff delay
        backoff_delay = self._calculate_backoff_delay(message.retry_count)
        
        # Increment retry count
        message.retry_count += 1
        
        # Schedule retry after backoff delay
        retry_timer = Timer(
            backoff_delay,
            self._attempt_message_retry,
            args=(message.message_id,),
        )
        retry_timer.daemon = True
        retry_timer.start()
        
        logger.debug(
            f"Scheduling retry {message.retry_count} for message {message.message_id} "
            f"after {backoff_delay:.2f}s backoff"
        )
    
    def _attempt_message_retry(self, message_id: UUID) -> None:
        """
        Attempt to retry message delivery per Lifecycle Playbooks (#15).
        
        Args:
            message_id: UUID of message to retry.
        """
        message = self._messages.get(message_id)
        if not message:
            return
        
        # Check if expired - don't retry expired messages per Functional Spec (#6), Section 4.4
        if message.is_expired():
            message.state = MessageState.EXPIRED
            logger.debug(f"Message {message_id} expired before retry")
            return
        
        # Check retry limit per Resolved TBDs
        if message.retry_count >= MAX_DELIVERY_RETRIES:
            message.state = MessageState.FAILED
            if self.log_service:
                self.log_service.log_event(
                    LOG_EVENT_DELIVERY_FAILED,
                    {
                        "message_id": str(message_id),
                        "device_id": self.device_id,
                        "retry_count": message.retry_count,
                        "timestamp": utc_now().isoformat(),
                    },
                )
            logger.warning(f"Message {message_id} failed after max retries")
            return
        
        # Attempt delivery
        success = False
        if self._websocket_connected and self.websocket_client:
            try:
                success = self._send_via_websocket(message)
            except Exception:
                pass
        
        if not success and self.http_client:
            try:
                success = self._send_via_rest(message)
            except Exception:
                pass
        
        if not success:
            # Queue for offline delivery or schedule another retry
            if message.retry_count < MAX_DELIVERY_RETRIES:
                self._retry_message_with_backoff(message)
            else:
                self._queue_message_offline(message)
    
    def process_offline_queue(self) -> None:
        """
        Process offline message queue per Lifecycle Playbooks (#15), Section 5.
        
        Attempts to deliver queued messages when network becomes available.
        Removes expired messages immediately per Resolved Clarifications.
        
        Note:
            Messages that exceed retry limits are marked as FAILED.
            Successfully delivered messages are removed from queue.
        """
        with self._queue_lock:
            # Remove expired messages first per Resolved Clarifications
            self._evict_expired_messages()
            
            # Process remaining queued messages
            messages_to_retry = list(self._queued_messages.values())
        
        for queued in messages_to_retry:
            message = queued.message
            
            # Check if should retry per Lifecycle Playbooks (#15)
            if not queued.should_retry():
                # Mark as failed if retries exhausted
                if message.retry_count >= MAX_DELIVERY_RETRIES:
                    message.state = MessageState.FAILED
                    if self.log_service:
                        self.log_service.log_event(
                            LOG_EVENT_DELIVERY_FAILED,
                            {
                                "message_id": str(message.message_id),
                                "device_id": self.device_id,
                                "retry_count": message.retry_count,
                                "timestamp": utc_now().isoformat(),
                            },
                        )
                continue
            
            # Calculate backoff delay based on retry count per Lifecycle Playbooks (#15)
            if queued.last_retry_at:
                # Calculate time since last retry for exponential backoff
                time_since_last_retry = (utc_now() - queued.last_retry_at).total_seconds()
                backoff_delay = self._calculate_backoff_delay(message.retry_count)
                
                # Skip if backoff period hasn't elapsed
                if time_since_last_retry < backoff_delay:
                    continue
            
            # Attempt delivery
            message.retry_count += 1
            queued.last_retry_at = utc_now()
            
            success = False
            if self._websocket_connected and self.websocket_client:
                try:
                    success = self._send_via_websocket(message)
                except Exception:
                    pass
            
            if not success and self.http_client:
                try:
                    success = self._send_via_rest(message)
                except Exception:
                    pass
            
            if success:
                # Remove from queue on successful delivery
                with self._queue_lock:
                    self._queued_messages.pop(message.message_id, None)
                    self._queued_storage_size -= len(message.payload)
                    message.state = MessageState.DELIVERED
            else:
                # Keep in queue for next retry with exponential backoff
                with self._queue_lock:
                    self._queued_messages[message.message_id] = queued
    
    def handle_websocket_disconnect(self) -> None:
        """
        Handle WebSocket disconnect per Resolved Clarifications (#51).
        
        Implements automatic reconnect with exponential backoff.
        Falls back to REST polling if reconnect fails >15s per Resolved Clarifications (#51).
        """
        self._websocket_connected = False
        
        # Cancel existing reconnect timer if any
        if self._websocket_reconnect_timer:
            self._websocket_reconnect_timer.cancel()
        
        # Start exponential backoff reconnect per Resolved Clarifications (#51)
        self._websocket_reconnect_attempts = 0
        self._schedule_websocket_reconnect()
        
        # Schedule fallback to REST polling after 15s per Resolved Clarifications (#51)
        fallback_timer = Timer(
            WEBSOCKET_RECONNECT_TIMEOUT_SECONDS,
            self._check_websocket_reconnect_fallback,
        )
        fallback_timer.daemon = True
        fallback_timer.start()
    
    def _schedule_websocket_reconnect(self) -> None:
        """
        Schedule WebSocket reconnect with exponential backoff per Resolved Clarifications (#51).
        
        Calculates backoff delay based on reconnect attempts.
        """
        if self._websocket_connected:
            return  # Already connected
        
        # Calculate exponential backoff delay
        backoff_delay = self._calculate_backoff_delay(self._websocket_reconnect_attempts)
        
        # Schedule reconnect attempt
        self._websocket_reconnect_timer = Timer(
            backoff_delay,
            self._attempt_websocket_reconnect,
        )
        self._websocket_reconnect_timer.daemon = True
        self._websocket_reconnect_timer.start()
        
        logger.debug(
            f"Scheduling WebSocket reconnect attempt {self._websocket_reconnect_attempts + 1} "
            f"after {backoff_delay:.2f}s backoff"
        )
    
    def _attempt_websocket_reconnect(self) -> None:
        """
        Attempt WebSocket reconnection per Resolved Clarifications (#51).
        
        Note: Actual reconnect logic is implemented in WebSocket client.
        This method triggers the reconnect attempt.
        """
        if self._websocket_connected:
            return  # Already connected
        
        self._websocket_reconnect_attempts += 1
        
        # Attempt reconnect (WebSocket client handles actual connection)
        if self.websocket_client:
            try:
                # WebSocket client should implement reconnect logic
                # For now, we assume reconnect is attempted
                # In a real implementation, this would call websocket_client.reconnect()
                logger.debug(f"Attempting WebSocket reconnect (attempt {self._websocket_reconnect_attempts})")
                
                # If reconnect successful, websocket client should call handle_websocket_connect()
                # Otherwise, schedule another reconnect
                if not self._websocket_connected:
                    self._schedule_websocket_reconnect()
            except Exception as e:
                logger.warning(f"WebSocket reconnect attempt failed: {e}")
                self._schedule_websocket_reconnect()
    
    def handle_websocket_connect(self) -> None:
        """
        Handle WebSocket connection established per Resolved Clarifications (#51).
        
        Resets reconnect attempts and stops REST polling if active.
        """
        self._websocket_connected = True
        self._websocket_reconnect_attempts = 0
        
        # Cancel reconnect timer
        if self._websocket_reconnect_timer:
            self._websocket_reconnect_timer.cancel()
            self._websocket_reconnect_timer = None
        
        # Stop REST polling if active (WebSocket is preferred)
        if self._rest_polling_active:
            self._stop_rest_polling()
        
        logger.debug("WebSocket connected, stopping REST polling fallback")
    
    def _check_websocket_reconnect_fallback(self) -> None:
        """
        Check if WebSocket reconnect has failed and fallback to REST polling per Resolved Clarifications (#51).
        
        If WebSocket still not connected after timeout, start REST polling fallback.
        """
        if not self._websocket_connected and not self._rest_polling_active:
            logger.info("WebSocket reconnect timeout, falling back to REST polling")
            self._start_rest_polling()
    
    def _start_rest_polling(self) -> None:
        """
        Start REST polling fallback per Resolved TBDs (#18).
        
        Polls every 30 seconds per Resolved TBDs (#18).
        Respects expiration and duplicate detection rules per Functional Spec (#6).
        """
        if self._rest_polling_active:
            return  # Already polling
        
        self._rest_polling_active = True
        self._rest_polling_stop_event.clear()
        
        # Start polling thread
        self._rest_polling_thread = Thread(
            target=self._rest_polling_loop,
            daemon=True,
        )
        self._rest_polling_thread.start()
        
        logger.debug("Started REST polling fallback (30s interval)")
    
    def _stop_rest_polling(self) -> None:
        """
        Stop REST polling fallback.
        
        Called when WebSocket reconnects (preferred method per Resolved TBDs).
        """
        if not self._rest_polling_active:
            return
        
        self._rest_polling_active = False
        self._rest_polling_stop_event.set()
        
        if self._rest_polling_thread and self._rest_polling_thread.is_alive():
            self._rest_polling_thread.join(timeout=5.0)
        
        logger.debug("Stopped REST polling fallback")
    
    def _rest_polling_loop(self) -> None:
        """
        REST polling loop per Resolved TBDs (#18) and API Contracts (#10), Section 3.4.
        
        Polls /api/message/receive every 30 seconds.
        Respects expiration and duplicate detection rules.
        """
        last_received_id: Optional[str] = None
        
        while self._rest_polling_active and not self._rest_polling_stop_event.is_set():
            if not self.http_client:
                break
            
            try:
                # Poll for messages per API Contracts (#10), Section 3.4
                headers = {HEADER_DEVICE_ID: self.device_id}
                params = {}
                if last_received_id:
                    params["last_received_id"] = last_received_id
                
                # Poll for messages per API Contracts (#10), Section 3.4
                response = self.http_client.get(
                    API_ENDPOINT_RECEIVE_MESSAGE,
                    params=params,
                    headers=headers,
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    messages = response_data.get("messages", [])
                    
                    # Process received messages per Functional Spec (#6), Section 4.3
                    for msg_data in messages:
                        try:
                            # Extract message data
                            msg_id = UUID(msg_data["message_id"])
                            encrypted_payload = bytes.fromhex(msg_data["payload"])
                            sender_id = msg_data["sender_id"]
                            conversation_id = msg_data.get("conversation_id", "")
                            expiration_timestamp = datetime.fromisoformat(msg_data["expiration"])
                            
                            # Receive message (handles expiration and duplicate detection)
                            received = self.receive_message(
                                message_id=msg_id,
                                encrypted_payload=encrypted_payload,
                                sender_id=sender_id,
                                conversation_id=conversation_id,
                                expiration_timestamp=expiration_timestamp,
                            )
                            
                            if received:
                                last_received_id = str(msg_id)
                                logger.debug(f"Received message {msg_id} via REST polling")
                        except (KeyError, ValueError, Exception) as e:
                            logger.warning(f"Error processing polled message: {e}")
                            continue
                
                # Wait for polling interval or stop event
                if self._rest_polling_stop_event.wait(REST_POLLING_INTERVAL_SECONDS):
                    break  # Stop event set
                
            except Exception as e:
                logger.warning(f"REST polling error: {e}")
                # Continue polling even on error
                if self._rest_polling_stop_event.wait(REST_POLLING_INTERVAL_SECONDS):
                    break
    
    def cleanup_expired_messages(self) -> None:
        """
        Cleanup expired messages on app start/reconnection per Data Classification (#8), Section 6.
        
        Expired messages deleted immediately upon reconnection per Resolved Clarifications.
        
        Note:
            Cleans up both active messages and offline queue.
        """
        current_time = utc_now()
        
        # Find and expire all expired messages
        expired_ids = [
            msg_id
            for msg_id, message in self._messages.items()
            if message.is_expired(current_time)
        ]
        
        for msg_id in expired_ids:
            self._expire_message(msg_id)
        
        # Clean up offline queue expired messages
        with self._queue_lock:
            self._evict_expired_messages()
