"""
Client-facing API types and DTOs for Abiqua Asset Management.

References:
- API Contracts (#10)
- UX Behavior (#12)
- Copy Rules (#13)
- Functional Specification (#6)
- Resolved Specs & Clarifications

This module defines client-safe data structures that hide internal implementation
details. Clients never see internal state machine names, retry counters, or
cryptographic material per UX Behavior (#12), Section 3.6.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from src.shared.message_types import utc_now


class ClientMessageState(Enum):
    """
    Client-visible message states per UX Behavior (#12), Section 4.
    
    These states map cleanly to UX behavior and hide internal state machine details.
    Clients never see: PendingDelivery, retry_count, or internal state names.
    """
    SENT = "sent"  # Maps to PendingDelivery (internal)
    DELIVERED = "delivered"  # Maps to Delivered (internal)
    FAILED = "failed"  # Maps to Failed (internal)
    EXPIRED = "expired"  # Maps to Expired (internal)
    READ_ONLY = "read_only"  # Neutral enterprise mode (revoked devices)


class ClientConversationState(Enum):
    """
    Client-visible conversation states per UX Behavior (#12), Section 3.2.
    
    Simplified states for client consumption.
    """
    ACTIVE = "active"
    CLOSED = "closed"


class ClientErrorCode(Enum):
    """
    Client-visible error codes per API Contracts (#10), Section 6.
    
    Error codes are deterministic and enumerated per Copy Rules (#13), Section 4.
    """
    INVALID_REQUEST = 400
    UNAUTHORIZED_DEVICE = 401
    REVOKED_DEVICE = 403
    RESOURCE_NOT_FOUND = 404
    BACKEND_FAILURE = 500


@dataclass
class ClientMessageDTO:
    """
    Client-facing message DTO per API Contracts (#10), Section 3.4.
    
    Hides internal implementation details:
    - No retry_count
    - No internal state machine names
    - No cryptographic material
    - Simplified state (SENT, DELIVERED, FAILED, EXPIRED)
    
    Classification: Restricted (metadata only) per Data Classification (#8), Section 3.
    """
    message_id: str  # UUID as string
    sender_id: str  # Device ID
    conversation_id: str  # Conversation identifier
    state: ClientMessageState  # Client-visible state
    created_at: datetime  # Creation timestamp (ISO format)
    expires_at: datetime  # Expiration timestamp (ISO format)
    # Note: payload is encrypted and sent separately per API Contracts (#10)


@dataclass
class ClientConversationDTO:
    """
    Client-facing conversation DTO per UX Behavior (#12), Section 3.2.
    
    Simplified conversation representation for client consumption.
    
    Classification: Restricted per Data Classification (#8), Section 3.
    """
    conversation_id: str  # Conversation identifier
    state: ClientConversationState  # Client-visible state
    participant_count: int  # Number of participants (not individual IDs for privacy)
    last_message_at: Optional[datetime] = None  # Last message timestamp for sorting
    created_at: datetime = None  # Creation timestamp
    
    def __post_init__(self) -> None:
        """Initialize created_at if not provided."""
        if self.created_at is None:
            self.created_at = utc_now()


@dataclass
class ClientErrorResponse:
    """
    Client-facing error response per API Contracts (#10), Section 6 and Copy Rules (#13), Section 4.
    
    Error responses are:
    - Deterministic (enumerated error codes)
    - Content-free (no sensitive information)
    - Neutral (no technical details exposed)
    """
    error_code: ClientErrorCode
    message: str  # Neutral error message per Copy Rules (#13), Section 4
    api_version: str = "v1"  # API version per API Contracts (#10)
    timestamp: datetime = None  # Error timestamp
    
    def __post_init__(self) -> None:
        """Initialize timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = utc_now()
    
    def to_dict(self) -> dict:
        """
        Convert error response to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation of error response.
        """
        return {
            "error_code": self.error_code.value,
            "message": self.message,
            "api_version": self.api_version,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ClientSuccessResponse:
    """
    Client-facing success response per API Contracts (#10).
    
    Standardized success response format with API versioning.
    """
    status: str = "success"
    api_version: str = "v1"  # API version per API Contracts (#10)
    data: Optional[dict] = None  # Response data (varies by endpoint)
    timestamp: datetime = None  # Response timestamp
    
    def __post_init__(self) -> None:
        """Initialize timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = utc_now()
    
    def to_dict(self) -> dict:
        """
        Convert success response to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation of success response.
        """
        result = {
            "status": self.status,
            "api_version": self.api_version,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.data is not None:
            result["data"] = self.data
        return result
