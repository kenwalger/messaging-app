"""
Shared message types and constants for Abiqua Asset Management.

References:
- Functional Specification (#6)
- State Machines (#7)
- Data Classification & Retention (#8)
- API Contracts (#10)
- Resolved Specs & Clarifications
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4


def utc_now() -> datetime:
    """
    Get current UTC time.
    
    Replaces deprecated datetime.utcnow() with timezone-aware datetime.
    References: Repo & Coding Standards (#17)
    """
    return datetime.now(timezone.utc)


# Constants per Resolved Specs & Clarifications
MAX_GROUP_SIZE = 50  # Max participants per conversation
DEFAULT_MESSAGE_EXPIRATION_DAYS = 7  # Default expiration period
MAX_OFFLINE_MESSAGES = 500  # Max messages queued offline
MAX_OFFLINE_STORAGE_MB = 50  # Max storage size in MB
MAX_MESSAGE_PAYLOAD_SIZE_KB = 50  # Max payload size in KB
MAX_DELIVERY_RETRIES = 5  # Max retry attempts before marking failed
REST_POLLING_INTERVAL_SECONDS = 30  # REST fallback polling interval
WEBSOCKET_RECONNECT_TIMEOUT_SECONDS = 15  # WebSocket reconnect timeout
CLOCK_SKEW_TOLERANCE_MINUTES = 2  # Acceptable clock skew tolerance


class MessageState(Enum):
    """
    Message lifecycle states per State Machines (#7), Section 3.
    
    State transitions:
    Created -> PendingDelivery -> Delivered/Failed -> Active -> Expired
    """
    CREATED = "created"
    PENDING_DELIVERY = "pending_delivery"
    DELIVERED = "delivered"
    FAILED = "failed"
    ACTIVE = "active"
    EXPIRED = "expired"


@dataclass
class Message:
    """
    Message data structure per Functional Spec (#6), Section 4.2.
    
    Classification: Confidential (Data Classification #8, Section 3)
    - Message content must be encrypted at rest and in transit
    - Never logged in plaintext
    """
    message_id: UUID  # UUID v4, client-generated per Resolved Clarifications
    sender_id: str  # Device-bound identity
    recipients: List[str]  # List of recipient device IDs (max 50 per Resolved TBDs)
    payload: bytes  # Encrypted message payload (max 50KB per Resolved TBDs)
    conversation_id: str  # Conversation identifier
    creation_timestamp: datetime  # Local device timestamp
    expiration_timestamp: datetime  # Expiration time (default 7 days per Resolved TBDs)
    state: MessageState  # Current state per State Machines (#7)
    retry_count: int = 0  # Retry attempts (max 5 per Resolved TBDs)
    
    def __post_init__(self):
        """Validate message constraints per Functional Spec (#6) and Resolved TBDs."""
        if len(self.recipients) > MAX_GROUP_SIZE:
            raise ValueError(f"Recipients exceed max group size of {MAX_GROUP_SIZE}")
        
        if len(self.payload) > MAX_MESSAGE_PAYLOAD_SIZE_KB * 1024:
            raise ValueError(f"Payload exceeds max size of {MAX_MESSAGE_PAYLOAD_SIZE_KB}KB")
        
        if self.retry_count > MAX_DELIVERY_RETRIES:
            raise ValueError(f"Retry count exceeds max of {MAX_DELIVERY_RETRIES}")
    
    def is_expired(self, current_time: Optional[datetime] = None) -> bool:
        """
        Check if message has expired per Functional Spec (#6), Section 4.4.
        
        Uses local device time per Functional Spec (#6), Section 10.
        """
        if current_time is None:
            current_time = utc_now()
        return current_time >= self.expiration_timestamp
    
    def calculate_expiration_timestamp(
        self, 
        expiration_days: int = DEFAULT_MESSAGE_EXPIRATION_DAYS
    ) -> datetime:
        """
        Calculate expiration timestamp per Resolved TBDs.
        
        Default: 7 days from creation.
        """
        return self.creation_timestamp + timedelta(days=expiration_days)


@dataclass
class QueuedMessage:
    """
    Message queued for offline delivery per Functional Spec (#6), Section 10.
    
    Messages are queued when network is unavailable or backend unreachable.
    Expired messages are removed immediately from queue per Resolved Clarifications.
    """
    message: Message
    queued_at: datetime
    last_retry_at: Optional[datetime] = None
    
    def should_retry(self, current_time: Optional[datetime] = None) -> bool:
        """
        Determine if message should be retried per Lifecycle Playbooks (#15).
        
        Retries only within expiration window, max 5 attempts per Resolved TBDs.
        """
        if current_time is None:
            current_time = utc_now()
        
        if self.message.is_expired(current_time):
            return False  # Expired messages not retried per Resolved Clarifications
        
        if self.message.retry_count >= MAX_DELIVERY_RETRIES:
            return False  # Max retries exceeded
        
        return True


@dataclass
class MessageMetadata:
    """
    Message metadata for delivery per API Contracts (#10), Section 3.3.
    
    Classification: Restricted (Data Classification #8, Section 3)
    - Delete immediately after delivery
    - Never persist post-expiration
    """
    message_id: UUID
    sender_id: str
    recipients: List[str]
    conversation_id: str
    expiration_timestamp: datetime
    # Note: payload is encrypted and handled separately per API Contracts (#10)


@dataclass
class DeliveryAcknowledgment:
    """
    WebSocket delivery acknowledgment per Resolved Clarifications.
    
    ACK per message ID to ensure deterministic delivery.
    """
    message_id: UUID
    acknowledged_at: datetime
    device_id: str
