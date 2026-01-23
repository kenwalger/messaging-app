"""
Conversation store abstraction for persistent conversation metadata storage.

Supports Redis-backed storage for Heroku multi-dyno deployments and in-memory
fallback for demo mode when Redis is unavailable.

References:
- Functional Specification (#6), Section 5.2
- Data Classification (#8) - Only metadata stored, no message content
- Logging & Observability (#14)
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Set
from uuid import uuid4

from src.shared.conversation_types import ConversationState

logger = logging.getLogger(__name__)

# Default TTL for conversations in Redis (30 minutes)
# Configurable via CONVERSATION_TTL_SECONDS environment variable
DEFAULT_CONVERSATION_TTL_SECONDS = 30 * 60

def get_conversation_ttl() -> int:
    """Get conversation TTL from environment or default."""
    ttl_str = os.getenv("CONVERSATION_TTL_SECONDS")
    if ttl_str:
        try:
            return int(ttl_str)
        except ValueError:
            logger.warning(f"Invalid CONVERSATION_TTL_SECONDS value: {ttl_str}, using default")
    return DEFAULT_CONVERSATION_TTL_SECONDS


class ConversationStore(ABC):
    """
    Abstract base class for conversation metadata storage.
    
    Stores only conversation metadata (ID, participants, state, timestamps).
    Does NOT store message content, encryption keys, or decrypted payloads.
    """
    
    @abstractmethod
    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """
        Get conversation metadata by ID.
        
        Args:
            conversation_id: Conversation identifier.
        
        Returns:
            Dictionary with conversation metadata or None if not found.
            Format: {
                "conversation_id": str,
                "participants": List[str],
                "state": str,
                "created_at": str (ISO 8601),
                "last_activity_at": str (ISO 8601),
            }
        """
        pass
    
    @abstractmethod
    def create_conversation(
        self,
        conversation_id: str,
        participants: List[str],
        state: ConversationState = ConversationState.ACTIVE,
    ) -> bool:
        """
        Create a new conversation.
        
        Args:
            conversation_id: Conversation identifier.
            participants: List of participant device IDs.
            state: Conversation state (default: ACTIVE).
        
        Returns:
            True if created successfully, False if already exists.
        """
        pass
    
    @abstractmethod
    def update_conversation(
        self,
        conversation_id: str,
        participants: Optional[List[str]] = None,
        state: Optional[ConversationState] = None,
    ) -> bool:
        """
        Update conversation metadata.
        
        Args:
            conversation_id: Conversation identifier.
            participants: New participant list (optional).
            state: New conversation state (optional).
        
        Returns:
            True if updated successfully, False if conversation not found.
        """
        pass
    
    @abstractmethod
    def add_participant(
        self,
        conversation_id: str,
        device_id: str,
    ) -> bool:
        """
        Add participant to conversation atomically.
        
        Must be implemented atomically to prevent race conditions in concurrent scenarios.
        
        Args:
            conversation_id: Conversation identifier.
            device_id: Device ID to add as participant.
        
        Returns:
            True if participant added, False if conversation not found, closed, or limit exceeded.
        """
        pass
    
    @abstractmethod
    def remove_participant(
        self,
        conversation_id: str,
        device_id: str,
    ) -> bool:
        """
        Remove participant from conversation atomically.
        
        Must be implemented atomically to prevent race conditions in concurrent scenarios.
        If all participants are removed, conversation transitions to Closed state.
        
        Args:
            conversation_id: Conversation identifier.
            device_id: Device ID to remove from participants.
        
        Returns:
            True if participant removed, False if conversation not found or participant not in conversation.
        """
        pass
    
    @abstractmethod
    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete conversation metadata.
        
        Args:
            conversation_id: Conversation identifier.
        
        Returns:
            True if deleted successfully, False if not found.
        """
        pass
    
    @abstractmethod
    def conversation_exists(self, conversation_id: str) -> bool:
        """
        Check if conversation exists.
        
        Args:
            conversation_id: Conversation identifier.
        
        Returns:
            True if conversation exists, False otherwise.
        """
        pass


class RedisConversationStore(ConversationStore):
    """
    Redis-backed conversation store for Heroku multi-dyno deployments.
    
    Uses Redis for persistent conversation metadata storage.
    Compatible with Heroku Redis addon via REDIS_URL environment variable.
    """
    
    def __init__(self, redis_url: Optional[str] = None, ttl_seconds: Optional[int] = None):
        """
        Initialize Redis conversation store.
        
        Args:
            redis_url: Redis connection URL (defaults to REDIS_URL env var).
            ttl_seconds: Time-to-live for conversations in seconds (defaults to CONVERSATION_TTL_SECONDS env var or 30 minutes).
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self.ttl_seconds = ttl_seconds if ttl_seconds is not None else get_conversation_ttl()
        self._redis_client = None
        self._connected = False
        
        if self.redis_url:
            try:
                import redis
                self._redis_client = redis.from_url(
                    self.redis_url,
                    decode_responses=True,  # Automatically decode JSON strings
                    socket_connect_timeout=5,
                    socket_timeout=5,
                )
                # Test connection
                self._redis_client.ping()
                self._connected = True
                logger.info(f"Redis conversation store connected: {self.redis_url[:20]}... (TTL: {self.ttl_seconds}s)")
            except ImportError:
                logger.warning("redis package not installed, falling back to in-memory store")
                self._connected = False
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}, falling back to in-memory store")
                self._connected = False
        else:
            logger.warning("REDIS_URL not set, Redis conversation store unavailable")
    
    def _get_key(self, conversation_id: str) -> str:
        """Get Redis key for conversation."""
        return f"conversation:{conversation_id}"
    
    def _ensure_connected(self) -> bool:
        """
        Ensure Redis connection is available.
        
        Uses cached connection status to avoid per-operation pings.
        Only pings when connection status is uncertain.
        """
        if not self._connected or not self._redis_client:
            return False
        # Don't ping on every operation - trust the connection unless we get an error
        # The redis client will raise exceptions on actual failures
        return True
    
    def _check_connection(self) -> bool:
        """
        Explicitly check Redis connection (for startup/health checks).
        
        Returns:
            True if connected, False otherwise.
        """
        if not self._connected or not self._redis_client:
            return False
        try:
            self._redis_client.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis connection lost: {e}")
            self._connected = False
            return False
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Get conversation metadata from Redis."""
        if not self._ensure_connected():
            return None
        
        try:
            key = self._get_key(conversation_id)
            data = self._redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error reading conversation from Redis: {e}")
            # Mark connection as potentially lost
            self._connected = False
            return None
    
    def create_conversation(
        self,
        conversation_id: str,
        participants: List[str],
        state: ConversationState = ConversationState.ACTIVE,
    ) -> bool:
        """Create conversation in Redis."""
        if not self._ensure_connected():
            return False
        
        try:
            key = self._get_key(conversation_id)
            # Check if already exists
            if self._redis_client.exists(key):
                return False
            
            now = datetime.utcnow().isoformat()
            data = {
                "conversation_id": conversation_id,
                "participants": participants,
                "state": state.value,
                "created_at": now,
                "last_activity_at": now,
            }
            
            # Store with TTL
            self._redis_client.setex(
                key,
                self.ttl_seconds,
                json.dumps(data),
            )
            logger.debug(f"Created conversation {conversation_id} in Redis with TTL {self.ttl_seconds}s")
            return True
        except Exception as e:
            logger.error(f"Error creating conversation in Redis: {e}")
            return False
    
    def update_conversation(
        self,
        conversation_id: str,
        participants: Optional[List[str]] = None,
        state: Optional[ConversationState] = None,
    ) -> bool:
        """
        Update conversation in Redis using atomic transaction with optimistic locking.
        
        Preserves remaining TTL instead of resetting it to avoid unexpected expiration timing.
        Uses Redis WATCH/MULTI/EXEC transaction to ensure atomicity and prevent race conditions.
        Retries up to 3 times if concurrent modification detected.
        """
        if not self._ensure_connected():
            return False
        
        key = self._get_key(conversation_id)
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Use WATCH for optimistic locking
                self._redis_client.watch(key)
                
                # Read current state and TTL
                existing_data = self._redis_client.get(key)
                remaining_ttl = self._redis_client.ttl(key)
                
                if not existing_data:
                    # Key doesn't exist (TTL=-2)
                    self._redis_client.unwatch()
                    return False
                
                existing = json.loads(existing_data)
                
                # Handle TTL values:
                # TTL=-2: Key doesn't exist (already handled above)
                # TTL=-1: Key exists but has no expiration (use default TTL)
                # TTL>=0: Key exists with expiration (preserve remaining time)
                if remaining_ttl == -1:
                    # Key has no expiration, use default TTL
                    remaining_ttl = self.ttl_seconds
                elif remaining_ttl < 0:
                    # Should not happen (TTL=-2 already handled), but use default as fallback
                    logger.warning(f"Unexpected TTL value {remaining_ttl} for conversation {conversation_id}, using default")
                    remaining_ttl = self.ttl_seconds
                
                # Update fields
                if participants is not None:
                    existing["participants"] = participants
                if state is not None:
                    existing["state"] = state.value
                existing["last_activity_at"] = datetime.utcnow().isoformat()
                
                # Atomic update with preserved TTL using MULTI/EXEC transaction
                pipe = self._redis_client.pipeline()
                pipe.multi()
                pipe.setex(
                    key,
                    remaining_ttl,
                    json.dumps(existing),
                )
                result = pipe.execute()
                
                # If result is None, WATCH detected concurrent modification
                if result is None:
                    if attempt < max_retries - 1:
                        logger.debug(f"Concurrent modification detected for {conversation_id}, retrying (attempt {attempt + 1})")
                        continue
                    else:
                        logger.warning(f"Failed to update {conversation_id} after {max_retries} attempts due to concurrent modifications")
                        return False
                
                logger.debug(f"Updated conversation {conversation_id} in Redis (TTL preserved: {remaining_ttl}s)")
                return True
            except Exception as e:
                self._redis_client.unwatch()
                if attempt < max_retries - 1:
                    logger.debug(f"Error updating conversation {conversation_id}, retrying: {e}")
                    continue
                else:
                    logger.error(f"Error updating conversation in Redis after {max_retries} attempts: {e}")
                    # Mark connection as potentially lost
                    self._connected = False
                    return False
        
        return False
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete conversation from Redis."""
        if not self._ensure_connected():
            return False
        
        try:
            key = self._get_key(conversation_id)
            deleted = self._redis_client.delete(key)
            return deleted > 0
        except Exception as e:
            logger.error(f"Error deleting conversation from Redis: {e}")
            return False
    
    def conversation_exists(self, conversation_id: str) -> bool:
        """Check if conversation exists in Redis."""
        if not self._ensure_connected():
            return False
        
        try:
            key = self._get_key(conversation_id)
            return self._redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Error checking conversation existence in Redis: {e}")
            # Mark connection as potentially lost
            self._connected = False
            return False
    
    def add_participant(
        self,
        conversation_id: str,
        device_id: str,
    ) -> bool:
        """
        Add participant to conversation atomically using Redis transaction with optimistic locking.
        
        Prevents race conditions in concurrent scenarios by using WATCH/MULTI/EXEC.
        Retries up to 3 times if concurrent modification detected.
        """
        if not self._ensure_connected():
            return False
        
        from src.shared.constants import MAX_GROUP_SIZE
        from src.shared.conversation_types import ConversationState
        
        key = self._get_key(conversation_id)
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Use WATCH for optimistic locking
                self._redis_client.watch(key)
                
                # Read current state and TTL
                existing_data = self._redis_client.get(key)
                remaining_ttl = self._redis_client.ttl(key)
                
                if not existing_data:
                    # Key doesn't exist (TTL=-2)
                    self._redis_client.unwatch()
                    return False
                
                existing = json.loads(existing_data)
                current_participants = set(existing["participants"])
                
                # Check if already a participant
                if device_id in current_participants:
                    self._redis_client.unwatch()
                    return True  # Already a participant
                
                # Check group size limit
                if len(current_participants) >= MAX_GROUP_SIZE:
                    self._redis_client.unwatch()
                    return False
                
                # Check conversation state
                if ConversationState(existing["state"]) != ConversationState.ACTIVE:
                    self._redis_client.unwatch()
                    return False
                
                # Add participant
                new_participants = list(current_participants) + [device_id]
                existing["participants"] = new_participants
                existing["last_activity_at"] = datetime.utcnow().isoformat()
                
                # Handle TTL
                if remaining_ttl == -1:
                    remaining_ttl = self.ttl_seconds
                elif remaining_ttl < 0:
                    remaining_ttl = self.ttl_seconds
                
                # Atomic update using MULTI/EXEC transaction
                pipe = self._redis_client.pipeline()
                pipe.multi()
                pipe.setex(key, remaining_ttl, json.dumps(existing))
                result = pipe.execute()
                
                # If result is None, WATCH detected concurrent modification
                if result is None:
                    if attempt < max_retries - 1:
                        logger.debug(f"Concurrent modification detected for {conversation_id} add_participant, retrying (attempt {attempt + 1})")
                        continue
                    else:
                        logger.warning(f"Failed to add participant {device_id} to {conversation_id} after {max_retries} attempts due to concurrent modifications")
                        return False
                
                logger.debug(f"Added participant {device_id} to conversation {conversation_id}")
                return True
            except Exception as e:
                self._redis_client.unwatch()
                if attempt < max_retries - 1:
                    logger.debug(f"Error adding participant to {conversation_id}, retrying: {e}")
                    continue
                else:
                    logger.error(f"Error adding participant in Redis after {max_retries} attempts: {e}")
                    self._connected = False
                    return False
        
        return False
    
    def remove_participant(
        self,
        conversation_id: str,
        device_id: str,
    ) -> bool:
        """
        Remove participant from conversation atomically using Redis transaction with optimistic locking.
        
        Prevents race conditions in concurrent scenarios by using WATCH/MULTI/EXEC.
        If all participants are removed, conversation transitions to Closed state.
        Retries up to 3 times if concurrent modification detected.
        """
        if not self._ensure_connected():
            return False
        
        from src.shared.conversation_types import ConversationState
        
        key = self._get_key(conversation_id)
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Use WATCH for optimistic locking
                self._redis_client.watch(key)
                
                # Read current state and TTL
                existing_data = self._redis_client.get(key)
                remaining_ttl = self._redis_client.ttl(key)
                
                if not existing_data:
                    # Key doesn't exist (TTL=-2)
                    self._redis_client.unwatch()
                    return False
                
                existing = json.loads(existing_data)
                current_participants = set(existing["participants"])
                
                if device_id not in current_participants:
                    self._redis_client.unwatch()
                    return False
                
                # Remove participant
                new_participants = list(current_participants - {device_id})
                existing["participants"] = new_participants
                existing["last_activity_at"] = datetime.utcnow().isoformat()
                
                # If no participants remain, close conversation
                if not new_participants:
                    existing["state"] = ConversationState.CLOSED.value
                
                # Handle TTL
                if remaining_ttl == -1:
                    remaining_ttl = self.ttl_seconds
                elif remaining_ttl < 0:
                    remaining_ttl = self.ttl_seconds
                
                # Atomic update using MULTI/EXEC transaction
                pipe = self._redis_client.pipeline()
                pipe.multi()
                pipe.setex(key, remaining_ttl, json.dumps(existing))
                result = pipe.execute()
                
                # If result is None, WATCH detected concurrent modification
                if result is None:
                    if attempt < max_retries - 1:
                        logger.debug(f"Concurrent modification detected for {conversation_id} remove_participant, retrying (attempt {attempt + 1})")
                        continue
                    else:
                        logger.warning(f"Failed to remove participant {device_id} from {conversation_id} after {max_retries} attempts due to concurrent modifications")
                        return False
                
                logger.debug(f"Removed participant {device_id} from conversation {conversation_id}")
                return True
            except Exception as e:
                self._redis_client.unwatch()
                if attempt < max_retries - 1:
                    logger.debug(f"Error removing participant from {conversation_id}, retrying: {e}")
                    continue
                else:
                    logger.error(f"Error removing participant in Redis after {max_retries} attempts: {e}")
                    self._connected = False
                    return False
        
        return False


class InMemoryConversationStore(ConversationStore):
    """
    In-memory conversation store (fallback for demo mode when Redis unavailable).
    
    Only used when DEMO_MODE=true and Redis is not available.
    State is lost on restart or across dynos.
    """
    
    def __init__(self):
        """Initialize in-memory conversation store."""
        self._conversations: Dict[str, Dict] = {}
        logger.warning("Using in-memory conversation store (state will be lost on restart)")
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Get conversation from memory."""
        return self._conversations.get(conversation_id)
    
    def create_conversation(
        self,
        conversation_id: str,
        participants: List[str],
        state: ConversationState = ConversationState.ACTIVE,
    ) -> bool:
        """Create conversation in memory."""
        if conversation_id in self._conversations:
            return False
        
        now = datetime.utcnow().isoformat()
        self._conversations[conversation_id] = {
            "conversation_id": conversation_id,
            "participants": participants,
            "state": state.value,
            "created_at": now,
            "last_activity_at": now,
        }
        return True
    
    def update_conversation(
        self,
        conversation_id: str,
        participants: Optional[List[str]] = None,
        state: Optional[ConversationState] = None,
    ) -> bool:
        """Update conversation in memory."""
        if conversation_id not in self._conversations:
            return False
        
        if participants is not None:
            self._conversations[conversation_id]["participants"] = participants
        if state is not None:
            self._conversations[conversation_id]["state"] = state.value
        self._conversations[conversation_id]["last_activity_at"] = datetime.utcnow().isoformat()
        return True
    
    def add_participant(
        self,
        conversation_id: str,
        device_id: str,
    ) -> bool:
        """Add participant to conversation in memory."""
        if conversation_id not in self._conversations:
            return False
        
        conversation = self._conversations[conversation_id]
        current_participants = set(conversation["participants"])
        
        # Check if already a participant
        if device_id in current_participants:
            return True
        
        # Check group size limit
        from src.shared.constants import MAX_GROUP_SIZE
        if len(current_participants) >= MAX_GROUP_SIZE:
            return False
        
        # Add participant
        conversation["participants"] = list(current_participants) + [device_id]
        conversation["last_activity_at"] = datetime.utcnow().isoformat()
        return True
    
    def remove_participant(
        self,
        conversation_id: str,
        device_id: str,
    ) -> bool:
        """Remove participant from conversation in memory."""
        if conversation_id not in self._conversations:
            return False
        
        conversation = self._conversations[conversation_id]
        current_participants = set(conversation["participants"])
        
        if device_id not in current_participants:
            return False
        
        # Remove participant
        new_participants = list(current_participants - {device_id})
        conversation["participants"] = new_participants
        conversation["last_activity_at"] = datetime.utcnow().isoformat()
        
        # If no participants remain, close conversation
        if not new_participants:
            conversation["state"] = ConversationState.CLOSED.value
        
        return True
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete conversation from memory."""
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            return True
        return False
    
    def conversation_exists(self, conversation_id: str) -> bool:
        """Check if conversation exists in memory."""
        return conversation_id in self._conversations


def create_conversation_store(demo_mode: bool = False) -> ConversationStore:
    """
    Create appropriate conversation store based on environment.
    
    Priority:
    1. Redis if REDIS_URL is available
    2. In-memory if DEMO_MODE=true and Redis unavailable
    3. Raise error if DEMO_MODE=false and Redis unavailable
    
    Args:
        demo_mode: Whether demo mode is enabled.
    
    Returns:
        ConversationStore instance.
    
    Raises:
        RuntimeError: If Redis unavailable and not in demo mode.
    """
    # Try Redis first
    redis_store = RedisConversationStore()
    if redis_store._connected:
        logger.info(f"Using Redis conversation store (TTL: {redis_store.ttl_seconds}s)")
        return redis_store
    
    # Fallback to in-memory only in demo mode
    if demo_mode:
        logger.warning("Redis unavailable, using in-memory store (demo mode only - state will be lost on restart)")
        return InMemoryConversationStore()
    
    # Production mode requires Redis
    raise RuntimeError(
        "Redis conversation store unavailable and DEMO_MODE=false. "
        "Set REDIS_URL environment variable or enable DEMO_MODE for development."
    )
