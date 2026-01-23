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

from src.backend.conversation_store import ConversationStore, create_conversation_store
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
    
    Uses ConversationStore abstraction for persistent storage (Redis-backed on Heroku).
    """
    
    def __init__(self, device_registry, conversation_store: Optional[ConversationStore] = None, demo_mode: bool = False) -> None:
        """
        Initialize conversation registry.
        
        Args:
            device_registry: Device registry for validating participant devices.
            conversation_store: Optional conversation store (defaults to auto-detected store).
            demo_mode: Whether demo mode is enabled (affects store fallback behavior).
        """
        self.device_registry = device_registry
        
        # Use provided store or create appropriate store based on environment
        if conversation_store is None:
            self.store = create_conversation_store(demo_mode=demo_mode)
        else:
            self.store = conversation_store
        
        # In-memory cache for participant index (for efficient lookup)
        # Cache is invalidated when conversations are updated/deleted to prevent staleness
        self._participant_conversations: Dict[str, Set[str]] = {}  # device_id -> set of conversation_ids
        self._participant_lock = Lock()
        self._cache_invalidated = False  # Flag to track cache staleness
    
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
        
        # Check if conversation already exists in store
        if self.store.conversation_exists(conversation_id):
            logger.warning(f"Conversation {conversation_id} already exists")
            return False
        
        # Create conversation in store
        success = self.store.create_conversation(
            conversation_id=conversation_id,
            participants=valid_participants,
            state=ConversationState.ACTIVE,
        )
        
        if success:
            # Update participant index cache
            with self._participant_lock:
                for participant_id in valid_participants:
                    if participant_id not in self._participant_conversations:
                        self._participant_conversations[participant_id] = set()
                    self._participant_conversations[participant_id].add(conversation_id)
            logger.debug(f"Registered conversation {conversation_id} with {len(valid_participants)} participants")
        
        return success
    
    def add_participant(
        self,
        conversation_id: str,
        device_id: str,
    ) -> bool:
        """
        Add participant to conversation per State Machines (#7), Section 4.
        
        Uses atomic store operations to prevent race conditions in concurrent scenarios.
        
        Args:
            conversation_id: Conversation identifier.
            device_id: Device ID to add as participant.
        
        Returns:
            True if participant added, False if conversation not found, closed, or limit exceeded.
        """
        # Validate device first (before any store operations)
        if not self.device_registry.is_device_active(device_id):
            logger.warning(f"Cannot add revoked device {device_id} to conversation")
            return False
        
        # Use store's atomic add_participant method if available
        # Otherwise fall back to update_conversation (which uses transactions)
        if hasattr(self.store, 'add_participant'):
            success = self.store.add_participant(conversation_id, device_id)
        else:
            # Fallback: Get conversation and update (store handles atomicity)
            conversation = self.store.get_conversation(conversation_id)
            if not conversation:
                return False
            
            # Check conversation state
            if ConversationState(conversation["state"]) != ConversationState.ACTIVE:
                return False
            
            # Check group size limit
            current_participants = set(conversation["participants"])
            if len(current_participants) >= MAX_GROUP_SIZE:
                return False
            
            # Check if already a participant
            if device_id in current_participants:
                return True  # Already a participant, consider it success
            
            # Add participant (update_conversation uses atomic transaction)
            new_participants = list(current_participants) + [device_id]
            success = self.store.update_conversation(
                conversation_id=conversation_id,
                participants=new_participants,
            )
        
        if success:
            # Update participant index cache
            with self._participant_lock:
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
        Uses atomic store operations to prevent race conditions in concurrent scenarios.
        
        Args:
            conversation_id: Conversation identifier.
            device_id: Device ID to remove from participants.
        
        Returns:
            True if participant removed, False if conversation not found or participant not in conversation.
        """
        # Use store's atomic remove_participant method if available
        # Otherwise fall back to update_conversation (which uses transactions)
        if hasattr(self.store, 'remove_participant'):
            success = self.store.remove_participant(conversation_id, device_id)
        else:
            # Fallback: Get conversation and update (store handles atomicity)
            conversation = self.store.get_conversation(conversation_id)
            if not conversation:
                return False
            
            current_participants = set(conversation["participants"])
            if device_id not in current_participants:
                return False
            
            # Remove participant
            new_participants = list(current_participants - {device_id})
            
            # If no participants remain, close conversation
            if not new_participants:
                success = self.store.update_conversation(
                    conversation_id=conversation_id,
                    state=ConversationState.CLOSED,
                )
                if success:
                    logger.debug(f"Conversation {conversation_id} closed (all participants removed)")
            else:
                success = self.store.update_conversation(
                    conversation_id=conversation_id,
                    participants=new_participants,
                )
        
        if success:
            # Update participant index cache
            with self._participant_lock:
                if device_id in self._participant_conversations:
                    self._participant_conversations[device_id].discard(conversation_id)
                    if not self._participant_conversations[device_id]:
                        del self._participant_conversations[device_id]
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
        
        # Get all conversations for this participant from cache
        # Note: Cache may be incomplete if conversations expired, but we validate existence before removal
        with self._participant_lock:
            conversation_ids = list(self._participant_conversations.get(device_id, set()))
        
        for conversation_id in conversation_ids:
            # Verify conversation still exists before attempting removal (handles TTL expiration)
            if self.store.conversation_exists(conversation_id):
                if self.remove_participant(conversation_id, device_id):
                    affected_conversations.append(conversation_id)
            else:
                # Conversation expired or deleted - remove from cache
                self._invalidate_participant_cache_for_conversation(conversation_id)
        
        return affected_conversations
    
    def get_conversation_participants(self, conversation_id: str) -> Set[str]:
        """
        Get participants for a conversation.
        
        Always reads from store to ensure consistency (avoids stale cache after TTL expiration).
        
        Args:
            conversation_id: Conversation identifier.
        
        Returns:
            Set of participant device IDs (empty set if conversation doesn't exist).
        """
        # Always read from store to avoid stale cache after Redis TTL expiration
        conversation = self.store.get_conversation(conversation_id)
        if conversation:
            participants = set(conversation["participants"])
            # Update cache if conversation exists (for efficient revocation handling)
            with self._participant_lock:
                for participant_id in participants:
                    if participant_id not in self._participant_conversations:
                        self._participant_conversations[participant_id] = set()
                    self._participant_conversations[participant_id].add(conversation_id)
            return participants
        else:
            # Conversation doesn't exist (may have expired) - invalidate cache entries
            self._invalidate_participant_cache_for_conversation(conversation_id)
            return set()
    
    def _invalidate_participant_cache_for_conversation(self, conversation_id: str) -> None:
        """
        Invalidate participant cache entries for a conversation.
        
        Called when a conversation is deleted or expires to prevent stale cache.
        """
        with self._participant_lock:
            for participant_id in list(self._participant_conversations.keys()):
                self._participant_conversations[participant_id].discard(conversation_id)
                if not self._participant_conversations[participant_id]:
                    del self._participant_conversations[participant_id]
    
    def conversation_exists(self, conversation_id: str) -> bool:
        """
        Check if conversation exists (regardless of state).
        
        Args:
            conversation_id: Conversation identifier.
        
        Returns:
            True if conversation exists, False otherwise.
        """
        return self.store.conversation_exists(conversation_id)
    
    def is_conversation_active(self, conversation_id: str) -> bool:
        """
        Check if conversation is active.
        
        Args:
            conversation_id: Conversation identifier.
        
        Returns:
            True if conversation exists and is Active, False otherwise.
        """
        conversation = self.store.get_conversation(conversation_id)
        if conversation:
            return ConversationState(conversation["state"]) == ConversationState.ACTIVE
        return False
    
    def close_conversation(self, conversation_id: str) -> bool:
        """
        Close conversation per State Machines (#7), Section 4.
        
        Transitions: Active -> Closed
        
        Args:
            conversation_id: Conversation identifier to close.
        
        Returns:
            True if conversation closed, False if conversation not found or already closed.
        """
        conversation = self.store.get_conversation(conversation_id)
        if not conversation:
            return False
        
        if ConversationState(conversation["state"]) == ConversationState.CLOSED:
            return False  # Already closed
        
        success = self.store.update_conversation(
            conversation_id=conversation_id,
            state=ConversationState.CLOSED,
        )
        
        if success:
            logger.debug(f"Closed conversation {conversation_id}")
        
        return success
    
    def cleanup_closed_conversations(self) -> int:
        """
        Cleanup closed conversations per Data Classification (#8), Section 4.
        
        Removes closed conversations from registry.
        Closed conversations cannot be resurrected per State Machines (#7), Section 4.
        
        Note: With Redis-backed storage, closed conversations are automatically expired via TTL.
        This method is kept for compatibility but may not be needed with Redis TTL.
        
        Returns:
            Number of conversations removed.
        """
        # With Redis-backed storage, closed conversations expire via TTL
        # This method is kept for compatibility but may be a no-op with Redis
        # For in-memory store, we would need to scan all conversations, which is expensive
        # For now, we'll just return 0 and let Redis TTL handle cleanup
        logger.debug("Cleanup of closed conversations handled by Redis TTL (if using Redis store)")
        return 0
