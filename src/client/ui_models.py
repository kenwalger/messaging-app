"""
UI domain models (view models) for Abiqua Asset Management.

References:
- UX Behavior (#12)
- Copy Rules (#13)
- Functional Specification (#6)
- Client-Facing API Boundary (latest)
- Resolved Specs & Clarifications

This module defines UI-facing domain models that are:
- Stateless beyond derived fields
- Deterministically derived from API responses
- Presentation-safe (no internal IDs, retry counters, or cryptographic internals)

UI domain models provide UX-ready state for rendering, including derived flags
for neutral enterprise mode, expiration, and failure states.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from src.shared.client_types import (
    ClientConversationDTO,
    ClientConversationState,
    ClientMessageDTO,
    ClientMessageState,
)


@dataclass(frozen=True)
class MessageViewModel:
    """
    UI domain model for message display per UX Behavior (#12), Section 3.3 and 3.4.
    
    Stateless view model deterministically derived from ClientMessageDTO.
    Provides derived UX flags for expiration, failure, and read-only states.
    
    Classification: Restricted (metadata only) per Data Classification (#8), Section 3.
    """
    message_id: str  # UUID as string (client-visible)
    sender_id: str  # Device ID (client-visible)
    conversation_id: str  # Conversation identifier (client-visible)
    state: ClientMessageState  # Client-visible state
    created_at: datetime  # Creation timestamp
    expires_at: datetime  # Expiration timestamp
    
    # Derived UX flags per UX Behavior (#12) and Resolved Clarifications (#38)
    is_expired: bool  # True if message is expired (deterministically derived)
    is_failed: bool  # True if message delivery failed (deterministically derived)
    is_read_only: bool  # True if in neutral enterprise mode (revoked device)
    
    @property
    def display_state(self) -> str:
        """
        Get display-friendly state string per Copy Rules (#13), Section 3.
        
        Returns:
            Display-friendly state string for UI rendering.
        """
        if self.is_expired:
            return "expired"  # Message removed per UX Behavior (#12), Section 3.4
        if self.is_failed:
            return "failed"  # Delivery failed per UX Behavior (#12), Section 3.6
        if self.state == ClientMessageState.SENT:
            return "queued"  # Message queued per UX Behavior (#12), Section 3.3
        if self.state == ClientMessageState.DELIVERED:
            return "delivered"  # Message displayed per UX Behavior (#12), Section 3.4
        return "unknown"


@dataclass(frozen=True)
class ParticipantViewModel:
    """
    UI domain model for participant display per UX Behavior (#12), Section 3.2.
    
    Simplified participant representation for UI consumption.
    Hides internal participant IDs beyond what's necessary for display.
    
    Classification: Restricted per Data Classification (#8), Section 3.
    """
    device_id: str  # Device ID (client-visible)
    display_name: Optional[str] = None  # Optional display name (if available)
    
    def __post_init__(self) -> None:
        """Validate participant view model."""
        if not self.device_id:
            raise ValueError("Participant device_id cannot be empty")


@dataclass(frozen=True)
class ConversationViewModel:
    """
    UI domain model for conversation display per UX Behavior (#12), Section 3.2.
    
    Stateless view model deterministically derived from ClientConversationDTO.
    Provides derived UX flags for sending, read-only mode, and closure.
    
    Classification: Restricted per Data Classification (#8), Section 3.
    """
    conversation_id: str  # Conversation identifier (client-visible)
    state: ClientConversationState  # Client-visible state
    participant_count: int  # Number of participants (privacy-preserving)
    can_send: bool  # True if messages can be sent (not read-only, not closed)
    is_read_only: bool  # True if in neutral enterprise mode (revoked device)
    send_disabled: bool  # True if sending is disabled (read-only or closed)
    last_message_at: Optional[datetime] = None  # Last message timestamp for sorting
    created_at: datetime = None  # Creation timestamp
    
    @property
    def display_name(self) -> str:
        """
        Get display-friendly conversation name per Copy Rules (#13), Section 3.
        
        Returns:
            Display-friendly conversation name for UI rendering.
        """
        if self.participant_count == 1:
            return "Conversation"  # Single participant per Copy Rules (#13)
        return f"Conversation ({self.participant_count} participants)"  # Multi-participant
    
    @property
    def sort_key(self) -> datetime:
        """
        Get sort key for reverse chronological ordering per Resolved Clarifications (#53).
        
        Newest first: last_message_at if available, otherwise created_at.
        
        Returns:
            Timestamp for sorting (newest first).
        """
        return self.last_message_at if self.last_message_at else self.created_at


@dataclass(frozen=True)
class DeviceStateViewModel:
    """
    UI domain model for device state display per UX Behavior (#12), Section 3.1 and 3.5.
    
    Provides derived UX flags for neutral enterprise mode (revoked devices).
    
    Classification: Restricted per Data Classification (#8), Section 3.
    """
    device_id: str  # Device ID (client-visible)
    is_read_only: bool  # True if in neutral enterprise mode (revoked device)
    can_send: bool  # True if device can send messages (not read-only)
    can_create_conversations: bool  # True if device can create conversations (not read-only)
    can_join_conversations: bool  # True if device can join conversations (not read-only)
    
    @property
    def display_status(self) -> str:
        """
        Get display-friendly device status per Copy Rules (#13), Section 3.
        
        Returns:
            Display-friendly status string for UI rendering.
        """
        if self.is_read_only:
            return "Messaging Disabled"  # Neutral message per Copy Rules (#13), Section 4
        return "Active Messaging"  # Active state per UX Behavior (#12), Section 4
