"""
Shared conversation types and state enums for Abiqua Asset Management.

References:
- Functional Specification (#6), Section 4.1
- State Machines (#7), Section 4
- Data Classification & Retention (#8), Section 3
- UX Behavior (#12), Section 3.2
- Resolved Specs & Clarifications
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Set
from uuid import UUID, uuid4

from src.shared.message_types import utc_now

# Import max group size constant per Resolved TBDs
from src.shared.constants import MAX_GROUP_SIZE


class ConversationState(Enum):
    """
    Conversation lifecycle states per State Machines (#7), Section 4.
    
    State transitions:
    Uncreated -> Active -> Closed
    
    Notes:
    - Conversation creation is explicit, no auto-discovery per State Machines (#7)
    - Closed conversations cannot be resurrected per State Machines (#7)
    """
    UNCREATED = "uncreated"
    ACTIVE = "active"
    CLOSED = "closed"


@dataclass
class Conversation:
    """
    Conversation data structure per Functional Spec (#6), Section 4.1 and State Machines (#7), Section 4.
    
    Classification: Restricted (Data Classification #8, Section 3)
    - Conversation membership is Restricted classification
    - Remove when conversation ends or participant revoked
    - Active conversations retained while participants exist
    """
    conversation_id: str  # Conversation identifier (UUID string format)
    participants: List[str]  # List of participant device IDs (max 50 per Resolved TBDs)
    state: ConversationState  # Current state per State Machines (#7), Section 4
    created_at: datetime  # Creation timestamp
    last_message_timestamp: Optional[datetime] = None  # Last message timestamp for UI display
    created_by: str = ""  # Device ID that created the conversation
    
    def __post_init__(self) -> None:
        """
        Validate conversation constraints per Functional Spec (#6) and Resolved TBDs.
        
        Raises:
            ValueError: If participants exceed max group size or conversation is invalid.
        """
        if len(self.participants) > MAX_GROUP_SIZE:
            raise ValueError(f"Participants exceed max group size of {MAX_GROUP_SIZE}")
        
        if len(self.participants) == 0:
            raise ValueError("Conversation must have at least one participant")
        
        # Ensure unique participants
        if len(self.participants) != len(set(self.participants)):
            raise ValueError("Conversation participants must be unique")
    
    def add_participant(self, device_id: str) -> bool:
        """
        Add participant to conversation per State Machines (#7), Section 4.
        
        Only allowed in Active state. Enforces max group size limit.
        
        Args:
            device_id: Device ID to add as participant.
        
        Returns:
            True if participant added, False if conversation is closed or limit exceeded.
        
        Raises:
            ValueError: If conversation is not in Active state.
        """
        if self.state != ConversationState.ACTIVE:
            raise ValueError(f"Cannot add participant to conversation in {self.state.value} state")
        
        if device_id in self.participants:
            return False  # Participant already exists
        
        if len(self.participants) >= MAX_GROUP_SIZE:
            return False  # Max group size reached
        
        self.participants.append(device_id)
        return True
    
    def remove_participant(self, device_id: str) -> bool:
        """
        Remove participant from conversation per State Machines (#7), Section 4.
        
        If all participants are removed, conversation transitions to Closed state.
        
        Args:
            device_id: Device ID to remove from participants.
        
        Returns:
            True if participant removed, False if participant not found.
        """
        if device_id not in self.participants:
            return False
        
        self.participants.remove(device_id)
        
        # If no participants remain, close conversation per State Machines (#7), Section 4
        if len(self.participants) == 0:
            self.state = ConversationState.CLOSED
        
        return True
    
    def has_participant(self, device_id: str) -> bool:
        """
        Check if device is a participant in the conversation.
        
        Args:
            device_id: Device ID to check.
        
        Returns:
            True if device is a participant, False otherwise.
        """
        return device_id in self.participants
    
    def is_active(self) -> bool:
        """
        Check if conversation is in Active state.
        
        Returns:
            True if conversation is Active, False otherwise.
        """
        return self.state == ConversationState.ACTIVE
    
    def is_closed(self) -> bool:
        """
        Check if conversation is in Closed state.
        
        Returns:
            True if conversation is Closed, False otherwise.
        """
        return self.state == ConversationState.CLOSED
    
    def can_send_messages(self) -> bool:
        """
        Check if messages can be sent to this conversation.
        
        Per Resolved Clarifications: Closed conversations do not accept new messages.
        
        Returns:
            True if conversation is Active, False if Closed or Uncreated.
        """
        return self.state == ConversationState.ACTIVE
    
    def update_last_message_timestamp(self, timestamp: datetime) -> None:
        """
        Update last message timestamp for UI display per UX Behavior (#12), Section 3.2.
        
        Args:
            timestamp: Timestamp of the most recent message.
        """
        if self.last_message_timestamp is None or timestamp > self.last_message_timestamp:
            self.last_message_timestamp = timestamp
