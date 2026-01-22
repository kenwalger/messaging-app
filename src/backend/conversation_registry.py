"""
Backend conversation registry service for Abiqua Asset Management.

Implements backend conversation membership tracking per:
- Functional Specification (#6), Section 5.2
- State Machines (#7), Section 4
- Data Classification & Retention (#8)
- Resolved Specs & Clarifications

This module handles:
- Conversation membership tracking (Restricted classification)
- Participant addition and removal
- Conversation closure when all participants revoked
- Metadata handling (no message content)
"""

import logging
from datetime import datetime
from threading import Lock
from typing import Dict, List, Optional, Set

from src.shared.constants import MAX_GROUP_SIZE
from src.shared.conversation_types import ConversationState
from src.shared.message_types import utc_now

# Configure logging per Logging & Observability (#14)
# Note: No conversation content logged per Data Classification (#8)
logger = logging.getLogger(__name__)


class ConversationRegistry:
    """
    Backend conversation registry per Functional Spec (#6), Section 5.2.
    
    Tracks conversation membership (Restricted classification per Data Classification #8, Section 3).
    Removes membership when conversation ends or participant revoked per Data Classification (#8), Section 4.
    """
    
    def __init__(self, device_registry) -> None:
        """
        Initialize conversation registry.
        
        Args:
            device_registry: Device registry for validating participant devices.
        """
        self.device_registry = device_registry
        
        # Conversation membership tracking per Data Classification (#8), Section 3
        # Classification: Restricted
        # Structure: conversation_id -> set of participant device IDs
        self._conversation_members: Dict[str, Set[str]] = {}
        self._conversation_states: Dict[str, ConversationState] = {}
        self._conversation_lock = Lock()
        
        # Participant index for efficient lookup
        self._participant_conversations: Dict[str, Set[str]] = {}  # device_id -> set of conversation_ids
    
    def register_conversation(
        self,
        conversation_id: str,
        participants: List[str],
    ) -> bool:
        """
        Register a new conversation per Functional Spec (#6), Section 4.1.
        
        Args:
            conversation_id: Conversation identifier.
            participants: List of participant device IDs (max 50 per Resolved TBDs).
        
        Returns:
            True if conversation registered, False if invalid or exceeds limits.
        """
        # Validate group size per Resolved TBDs
        if len(participants) > MAX_GROUP_SIZE:
            logger.warning(f"Conversation {conversation_id} exceeds max group size: {len(participants)}")
            return False
        
        # Validate participants
        if not participants:
            logger.warning(f"Conversation {conversation_id} has no participants")
            return False
        
        # Validate participant devices
        valid_participants = [
            pid for pid in participants
            if self.device_registry.is_device_active(pid)
        ]
        
        if not valid_participants:
            logger.warning(f"Conversation {conversation_id} has no valid active participants")
            return False
        
        with self._conversation_lock:
            # Register conversation in Active state per State Machines (#7), Section 4
            self._conversation_members[conversation_id] = set(valid_participants)
            self._conversation_states[conversation_id] = ConversationState.ACTIVE
            
            # Update participant index
            for participant_id in valid_participants:
                if participant_id not in self._participant_conversations:
                    self._participant_conversations[participant_id] = set()
                self._participant_conversations[participant_id].add(conversation_id)
        
        logger.debug(f"Registered conversation {conversation_id} with {len(valid_participants)} participants")
        
        return True
    
    def add_participant(
        self,
        conversation_id: str,
        device_id: str,
    ) -> bool:
        """
        Add participant to conversation per State Machines (#7), Section 4.
        
        Args:
            conversation_id: Conversation identifier.
            device_id: Device ID to add as participant.
        
        Returns:
            True if participant added, False if conversation not found, closed, or limit exceeded.
        """
        with self._conversation_lock:
            if conversation_id not in self._conversation_members:
                return False
            
            # Check conversation state
            if self._conversation_states.get(conversation_id) != ConversationState.ACTIVE:
                return False
            
            # Check group size limit
            if len(self._conversation_members[conversation_id]) >= MAX_GROUP_SIZE:
                return False
            
            # Validate device
            if not self.device_registry.is_device_active(device_id):
                logger.warning(f"Cannot add revoked device {device_id} to conversation")
                return False
            
            # Add participant
            self._conversation_members[conversation_id].add(device_id)
            
            # Update participant index
            if device_id not in self._participant_conversations:
                self._participant_conversations[device_id] = set()
            self._participant_conversations[device_id].add(conversation_id)
        
        logger.debug(f"Added participant {device_id} to conversation {conversation_id}")
        
        return True
    
    def remove_participant(
        self,
        conversation_id: str,
        device_id: str,
    ) -> bool:
        """
        Remove participant from conversation per State Machines (#7), Section 4.
        
        If all participants are removed, conversation transitions to Closed state.
        
        Args:
            conversation_id: Conversation identifier.
            device_id: Device ID to remove from participants.
        
        Returns:
            True if participant removed, False if conversation not found or participant not in conversation.
        """
        with self._conversation_lock:
            if conversation_id not in self._conversation_members:
                return False
            
            if device_id not in self._conversation_members[conversation_id]:
                return False
            
            # Remove participant
            self._conversation_members[conversation_id].discard(device_id)
            
            # Update participant index
            if device_id in self._participant_conversations:
                self._participant_conversations[device_id].discard(conversation_id)
                if not self._participant_conversations[device_id]:
                    del self._participant_conversations[device_id]
            
            # If no participants remain, close conversation per State Machines (#7), Section 4
            if not self._conversation_members[conversation_id]:
                self._conversation_states[conversation_id] = ConversationState.CLOSED
                logger.debug(f"Conversation {conversation_id} closed (all participants removed)")
        
        logger.debug(f"Removed participant {device_id} from conversation {conversation_id}")
        
        return True
    
    def handle_participant_revocation(self, device_id: str) -> List[str]:
        """
        Handle participant revocation per State Machines (#7), Section 4.
        
        Removes revoked participant from all conversations.
        Closes conversations where all participants are revoked.
        
        Args:
            device_id: Revoked device identifier.
        
        Returns:
            List of conversation IDs that were affected (participant removed or conversation closed).
        """
        affected_conversations: List[str] = []
        
        with self._conversation_lock:
            # Get all conversations for this participant
            conversation_ids = list(self._participant_conversations.get(device_id, set()))
        
        for conversation_id in conversation_ids:
            if self.remove_participant(conversation_id, device_id):
                affected_conversations.append(conversation_id)
        
        return affected_conversations
    
    def get_conversation_participants(self, conversation_id: str) -> Set[str]:
        """
        Get participants for a conversation.
        
        Args:
            conversation_id: Conversation identifier.
        
        Returns:
            Set of participant device IDs (empty set if conversation doesn't exist).
        """
        with self._conversation_lock:
            return self._conversation_members.get(conversation_id, set()).copy()
    
    def conversation_exists(self, conversation_id: str) -> bool:
        """
        Check if conversation exists (regardless of state).
        
        Args:
            conversation_id: Conversation identifier.
        
        Returns:
            True if conversation exists in states dict, False otherwise.
        """
        with self._conversation_lock:
            return conversation_id in self._conversation_states
    
    def is_conversation_active(self, conversation_id: str) -> bool:
        """
        Check if conversation is active.
        
        Args:
            conversation_id: Conversation identifier.
        
        Returns:
            True if conversation exists and is Active, False otherwise.
        """
        with self._conversation_lock:
            return (
                conversation_id in self._conversation_states
                and self._conversation_states[conversation_id] == ConversationState.ACTIVE
            )
    
    def close_conversation(self, conversation_id: str) -> bool:
        """
        Close conversation per State Machines (#7), Section 4.
        
        Transitions: Active -> Closed
        
        Args:
            conversation_id: Conversation identifier to close.
        
        Returns:
            True if conversation closed, False if conversation not found or already closed.
        """
        with self._conversation_lock:
            if conversation_id not in self._conversation_states:
                return False
            
            if self._conversation_states[conversation_id] == ConversationState.CLOSED:
                return False  # Already closed
            
            # Transition to Closed state per State Machines (#7), Section 4
            self._conversation_states[conversation_id] = ConversationState.CLOSED
        
        logger.debug(f"Closed conversation {conversation_id}")
        
        return True
    
    def cleanup_closed_conversations(self) -> int:
        """
        Cleanup closed conversations per Data Classification (#8), Section 4.
        
        Removes closed conversations from registry.
        Closed conversations cannot be resurrected per State Machines (#7), Section 4.
        
        Returns:
            Number of conversations removed.
        """
        with self._conversation_lock:
            closed_conversation_ids = [
                cid for cid, state in self._conversation_states.items()
                if state == ConversationState.CLOSED
            ]
            
            for conversation_id in closed_conversation_ids:
                # Remove conversation
                self._conversation_members.pop(conversation_id, None)
                self._conversation_states.pop(conversation_id, None)
                
                # Remove from participant index
                for participant_id in list(self._participant_conversations.keys()):
                    self._participant_conversations[participant_id].discard(conversation_id)
                    if not self._participant_conversations[participant_id]:
                        del self._participant_conversations[participant_id]
        
        logger.debug(f"Cleaned up {len(closed_conversation_ids)} closed conversations")
        
        return len(closed_conversation_ids)
