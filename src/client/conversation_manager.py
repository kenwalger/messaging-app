"""
Client-side conversation management module for Abiqua Asset Management.

Implements conversation creation, state management, and participant handling per:
- Functional Specification (#6), Section 4.1
- State Machines (#7), Section 4
- Data Classification & Retention (#8)
- UX Behavior (#12), Section 3.2
- Resolved Specs & Clarifications

This module handles:
- Conversation creation with explicit participant definition
- Conversation state transitions (Uncreated -> Active -> Closed)
- Participant addition and removal
- Conversation closure when all participants revoked
- Integration with message delivery module
- Neutral enterprise mode support (read-only for revoked devices)
"""

import logging
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional, Protocol, Set
from uuid import uuid4

from src.shared.constants import MAX_GROUP_SIZE
from src.shared.conversation_types import (
    Conversation,
    ConversationState,
)
from src.shared.message_types import utc_now

# Configure logging per Logging & Observability (#14)
# Note: No conversation content logged per Data Classification (#8)
logger = logging.getLogger(__name__)


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


class ConversationManager:
    """
    Conversation management service per Functional Spec (#6), Section 4.1 and State Machines (#7), Section 4.
    
    Handles complete conversation lifecycle from creation to closure.
    """
    
    def __init__(
        self,
        device_id: str,
        device_registry: Optional[DeviceRegistry] = None,
        log_service: Optional[LogService] = None,
        device_revoked: bool = False,
    ) -> None:
        """
        Initialize conversation manager.
        
        Args:
            device_id: Device-bound identity per Identity Provisioning (#11).
            device_registry: Optional registry for validating participant devices.
            log_service: Optional logging service for operational events per
                Logging & Observability (#14).
            device_revoked: Whether this device is revoked (neutral enterprise mode per
                Resolved Clarifications).
        """
        self.device_id = device_id
        self.device_registry = device_registry
        self.log_service = log_service
        self.device_revoked = device_revoked
        
        # Conversation storage per State Machines (#7), Section 4
        # Classification: Restricted per Data Classification (#8), Section 3
        self._conversations: Dict[str, Conversation] = {}
        self._conversation_lock = Lock()
        
        # Track conversations by participant for efficient lookup
        self._participant_conversations: Dict[str, Set[str]] = {}  # device_id -> set of conversation_ids
    
    def create_conversation(
        self,
        participants: List[str],
        conversation_id: Optional[str] = None,
    ) -> Conversation:
        """
        Create a new conversation per Functional Spec (#6), Section 4.1 and State Machines (#7), Section 4.
        
        Conversations are explicitly created with explicitly defined participants.
        No implicit conversation discovery exists per Functional Spec (#6), Section 4.1.
        
        Transitions: Uncreated -> Active per State Machines (#7), Section 4.
        
        Args:
            participants: List of participant device IDs (max 50 per Resolved TBDs).
                Must include this device (self.device_id).
            conversation_id: Optional conversation identifier. If None, generates UUID v4.
        
        Returns:
            Conversation object in Active state per State Machines (#7), Section 4.
        
        Raises:
            ValueError: If constraints violated (group size, empty participants, device revoked).
            RuntimeError: If device is revoked (neutral enterprise mode per Resolved Clarifications).
        """
        # Check if device is revoked per Resolved Clarifications
        if self.device_revoked:
            raise RuntimeError("Cannot create conversations in neutral enterprise mode (device revoked)")
        
        # Validate participants list
        if not participants:
            raise ValueError("Conversation must have at least one participant")
        
        # Ensure this device is included in participants
        if self.device_id not in participants:
            participants = [self.device_id] + participants
        
        # Validate group size per Resolved TBDs
        if len(participants) > MAX_GROUP_SIZE:
            raise ValueError(f"Participants exceed max group size of {MAX_GROUP_SIZE}")
        
        # Validate participant devices if registry available
        if self.device_registry:
            valid_participants = [
                pid for pid in participants
                if self.device_registry.is_device_active(pid)
            ]
            if not valid_participants:
                raise ValueError("No valid active participants for conversation")
            participants = valid_participants
        
        # Generate conversation ID if not provided
        if conversation_id is None:
            conversation_id = str(uuid4())
        
        # Check if conversation already exists
        if conversation_id in self._conversations:
            raise ValueError(f"Conversation {conversation_id} already exists")
        
        # Create conversation in Active state per State Machines (#7), Section 4
        # Transition: Uncreated -> Active (implicit, created directly in Active state)
        conversation = Conversation(
            conversation_id=conversation_id,
            participants=participants,
            state=ConversationState.ACTIVE,
            created_at=utc_now(),
            created_by=self.device_id,
        )
        
        with self._conversation_lock:
            # Store conversation
            self._conversations[conversation_id] = conversation
            
            # Update participant index
            for participant_id in participants:
                if participant_id not in self._participant_conversations:
                    self._participant_conversations[participant_id] = set()
                self._participant_conversations[participant_id].add(conversation_id)
        
        # Log conversation creation per Logging & Observability (#14)
        if self.log_service:
            self.log_service.log_event(
                "conversation_created",
                {
                    "conversation_id": conversation_id,
                    "created_by": self.device_id,
                    "participant_count": len(participants),
                    "timestamp": conversation.created_at.isoformat(),
                },
            )
        
        logger.debug(f"Created conversation {conversation_id} with {len(participants)} participants")
        
        return conversation
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        Get conversation by ID.
        
        Args:
            conversation_id: Conversation identifier.
        
        Returns:
            Conversation object if found, None otherwise.
        """
        return self._conversations.get(conversation_id)
    
    def get_active_conversations(self) -> List[Conversation]:
        """
        Get all active conversations per UX Behavior (#12), Section 3.2.
        
        Display active conversations only per UX Behavior (#12), Section 3.2.
        
        Returns:
            List of active conversations sorted by last message timestamp (most recent first).
        """
        with self._conversation_lock:
            active_conversations = [
                conv for conv in self._conversations.values()
                if conv.state == ConversationState.ACTIVE
            ]
        
        # Sort by last message timestamp (most recent first) per Resolved TBDs
        # Conversations without messages appear last
        active_conversations.sort(
            key=lambda c: c.last_message_timestamp or c.created_at,
            reverse=True,
        )
        
        return active_conversations
    
    def get_conversations_for_participant(self, device_id: str) -> List[Conversation]:
        """
        Get all conversations for a specific participant.
        
        Args:
            device_id: Participant device ID.
        
        Returns:
            List of conversations where device is a participant.
        """
        with self._conversation_lock:
            conversation_ids = self._participant_conversations.get(device_id, set())
            conversations = [
                self._conversations[cid]
                for cid in conversation_ids
                if cid in self._conversations
            ]
        
        return conversations
    
    def add_participant(
        self,
        conversation_id: str,
        device_id: str,
    ) -> bool:
        """
        Add participant to conversation per State Machines (#7), Section 4.
        
        Only allowed in Active state. Enforces max group size limit.
        
        Args:
            conversation_id: Conversation identifier.
            device_id: Device ID to add as participant.
        
        Returns:
            True if participant added, False if conversation not found, closed, or limit exceeded.
        
        Raises:
            RuntimeError: If device is revoked (neutral enterprise mode per Resolved Clarifications).
        """
        # Check if device is revoked per Resolved Clarifications
        if self.device_revoked:
            raise RuntimeError("Cannot modify conversations in neutral enterprise mode (device revoked)")
        
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return False
        
        # Validate device if registry available
        if self.device_registry and not self.device_registry.is_device_active(device_id):
            logger.warning(f"Cannot add revoked device {device_id} to conversation")
            return False
        
        # Add participant (validates state and group size internally)
        try:
            success = conversation.add_participant(device_id)
        except ValueError:
            # Conversation is closed or invalid state per State Machines (#7), Section 4
            return False
        
        if success:
            with self._conversation_lock:
                # Update participant index
                if device_id not in self._participant_conversations:
                    self._participant_conversations[device_id] = set()
                self._participant_conversations[device_id].add(conversation_id)
            
            logger.debug(f"Added participant {device_id} to conversation {conversation_id}")
        
        return success
    
    def remove_participant(
        self,
        conversation_id: str,
        device_id: str,
    ) -> bool:
        """
        Remove participant from conversation per State Machines (#7), Section 4.
        
        If all participants are removed, conversation transitions to Closed state.
        Active -> Active (if other participants remain) or Active -> Closed (if all removed).
        
        Args:
            conversation_id: Conversation identifier.
            device_id: Device ID to remove from participants.
        
        Returns:
            True if participant removed, False if conversation not found or participant not in conversation.
        
        Note:
            If conversation closes (all participants removed), it transitions to Closed state
            per State Machines (#7), Section 4.
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return False
        
        # Remove participant (may close conversation if last participant)
        success = conversation.remove_participant(device_id)
        
        if success:
            with self._conversation_lock:
                # Update participant index
                if device_id in self._participant_conversations:
                    self._participant_conversations[device_id].discard(conversation_id)
                    if not self._participant_conversations[device_id]:
                        del self._participant_conversations[device_id]
            
            # If conversation closed, log event per Logging & Observability (#14)
            if conversation.state == ConversationState.CLOSED:
                if self.log_service:
                    self.log_service.log_event(
                        "conversation_closed",
                        {
                            "conversation_id": conversation_id,
                            "closed_by": self.device_id,
                            "timestamp": utc_now().isoformat(),
                        },
                    )
                logger.debug(f"Conversation {conversation_id} closed (all participants removed)")
            
            logger.debug(f"Removed participant {device_id} from conversation {conversation_id}")
        
        return success
    
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
            conversation = self.get_conversation(conversation_id)
            if not conversation:
                continue
            
            # Remove participant (may close conversation)
            if self.remove_participant(conversation_id, device_id):
                affected_conversations.append(conversation_id)
        
        return affected_conversations
    
    def close_conversation(self, conversation_id: str) -> bool:
        """
        Close conversation per State Machines (#7), Section 4.
        
        Transitions: Active -> Closed
        
        All messages in closed conversation remain until expiration per Resolved Clarifications.
        No new messages accepted in closed conversations per Resolved Clarifications.
        
        Args:
            conversation_id: Conversation identifier to close.
        
        Returns:
            True if conversation closed, False if conversation not found or already closed.
        
        Raises:
            RuntimeError: If device is revoked (neutral enterprise mode per Resolved Clarifications).
        """
        # Check if device is revoked per Resolved Clarifications
        if self.device_revoked:
            raise RuntimeError("Cannot modify conversations in neutral enterprise mode (device revoked)")
        
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return False
        
        if conversation.state == ConversationState.CLOSED:
            return False  # Already closed
        
        # Transition to Closed state per State Machines (#7), Section 4
        conversation.state = ConversationState.CLOSED
        
        # Log conversation closure per Logging & Observability (#14)
        if self.log_service:
            self.log_service.log_event(
                "conversation_closed",
                {
                    "conversation_id": conversation_id,
                    "closed_by": self.device_id,
                    "timestamp": utc_now().isoformat(),
                },
            )
        
        logger.debug(f"Closed conversation {conversation_id}")
        
        return True
    
    def can_send_to_conversation(self, conversation_id: str) -> bool:
        """
        Check if messages can be sent to conversation per Resolved Clarifications.
        
        Closed conversations do not accept new messages per Resolved Clarifications.
        Revoked devices cannot send messages per Resolved Clarifications.
        
        Args:
            conversation_id: Conversation identifier.
        
        Returns:
            True if conversation is Active and device is not revoked, False otherwise.
        """
        if self.device_revoked:
            return False  # Revoked devices cannot send messages per Resolved Clarifications
        
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return False
        
        return conversation.can_send_messages()
    
    def update_conversation_last_message(
        self,
        conversation_id: str,
        message_timestamp: datetime,
    ) -> bool:
        """
        Update conversation last message timestamp for UI display per UX Behavior (#12), Section 3.2.
        
        Args:
            conversation_id: Conversation identifier.
            message_timestamp: Timestamp of the message.
        
        Returns:
            True if conversation found and updated, False otherwise.
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return False
        
        conversation.update_last_message_timestamp(message_timestamp)
        return True
    
    def cleanup_closed_conversations(self) -> int:
        """
        Cleanup closed conversations per Data Classification (#8), Section 4.
        
        Removes closed conversations from storage.
        Closed conversations cannot be resurrected per State Machines (#7), Section 4.
        
        Returns:
            Number of conversations removed.
        """
        with self._conversation_lock:
            closed_conversation_ids = [
                cid for cid, conv in self._conversations.items()
                if conv.state == ConversationState.CLOSED
            ]
            
            for conversation_id in closed_conversation_ids:
                conversation = self._conversations.pop(conversation_id, None)
                if conversation:
                    # Remove from participant index
                    for participant_id in conversation.participants:
                        if participant_id in self._participant_conversations:
                            self._participant_conversations[participant_id].discard(conversation_id)
                            if not self._participant_conversations[participant_id]:
                                del self._participant_conversations[participant_id]
        
        logger.debug(f"Cleaned up {len(closed_conversation_ids)} closed conversations")
        
        return len(closed_conversation_ids)
    
    def handle_device_revocation(self) -> None:
        """
        Handle device revocation per Functional Spec (#6), Section 6.2 and Resolved Clarifications.
        
        Device enters neutral enterprise mode:
        - Can read historical messages per Resolved Clarifications
        - Can view conversation list per Resolved Clarifications
        - Cannot send messages per Resolved Clarifications
        - Cannot create new conversations per Resolved Clarifications
        
        Note:
            This method marks the device as revoked. Actual conversation cleanup
            is handled by handle_participant_revocation when this device is revoked
            by a controller.
        """
        self.device_revoked = True
        logger.debug(f"Device {self.device_id} revoked, entering neutral enterprise mode")
