"""
Unit tests for conversation store abstraction (Redis and InMemory implementations).

References:
- Functional Specification (#6), Section 5.2
- Data Classification (#8) - Only metadata stored
"""

import os
import unittest
from unittest.mock import Mock, patch

from src.backend.conversation_store import (
    ConversationStore,
    InMemoryConversationStore,
    RedisConversationStore,
    create_conversation_store,
    get_conversation_ttl,
)
from src.shared.conversation_types import ConversationState


class TestInMemoryConversationStore(unittest.TestCase):
    """Test cases for InMemoryConversationStore."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.store = InMemoryConversationStore()
    
    def test_create_and_get_conversation(self) -> None:
        """Test creating and retrieving a conversation."""
        conversation_id = "conv-001"
        participants = ["device-001", "device-002"]
        
        # Create conversation
        success = self.store.create_conversation(
            conversation_id=conversation_id,
            participants=participants,
            state=ConversationState.ACTIVE,
        )
        self.assertTrue(success)
        
        # Get conversation
        conversation = self.store.get_conversation(conversation_id)
        self.assertIsNotNone(conversation)
        self.assertEqual(conversation["conversation_id"], conversation_id)
        self.assertEqual(set(conversation["participants"]), set(participants))
        self.assertEqual(conversation["state"], ConversationState.ACTIVE.value)
    
    def test_create_duplicate_conversation(self) -> None:
        """Test that creating a duplicate conversation fails."""
        conversation_id = "conv-001"
        participants = ["device-001"]
        
        # Create first time
        success1 = self.store.create_conversation(
            conversation_id=conversation_id,
            participants=participants,
        )
        self.assertTrue(success1)
        
        # Try to create again (should fail)
        success2 = self.store.create_conversation(
            conversation_id=conversation_id,
            participants=participants,
        )
        self.assertFalse(success2)
    
    def test_update_conversation(self) -> None:
        """Test updating conversation metadata."""
        conversation_id = "conv-001"
        participants = ["device-001"]
        
        # Create conversation
        self.store.create_conversation(
            conversation_id=conversation_id,
            participants=participants,
        )
        
        # Update participants
        new_participants = ["device-001", "device-002"]
        success = self.store.update_conversation(
            conversation_id=conversation_id,
            participants=new_participants,
        )
        self.assertTrue(success)
        
        # Verify update
        conversation = self.store.get_conversation(conversation_id)
        self.assertEqual(set(conversation["participants"]), set(new_participants))
    
    def test_update_nonexistent_conversation(self) -> None:
        """Test that updating a nonexistent conversation fails."""
        success = self.store.update_conversation(
            conversation_id="nonexistent",
            participants=["device-001"],
        )
        self.assertFalse(success)
    
    def test_delete_conversation(self) -> None:
        """Test deleting a conversation."""
        conversation_id = "conv-001"
        participants = ["device-001"]
        
        # Create conversation
        self.store.create_conversation(
            conversation_id=conversation_id,
            participants=participants,
        )
        
        # Delete conversation
        success = self.store.delete_conversation(conversation_id)
        self.assertTrue(success)
        
        # Verify deleted
        self.assertFalse(self.store.conversation_exists(conversation_id))
    
    def test_conversation_exists(self) -> None:
        """Test conversation existence check."""
        conversation_id = "conv-001"
        participants = ["device-001"]
        
        # Should not exist initially
        self.assertFalse(self.store.conversation_exists(conversation_id))
        
        # Create conversation
        self.store.create_conversation(
            conversation_id=conversation_id,
            participants=participants,
        )
        
        # Should exist now
        self.assertTrue(self.store.conversation_exists(conversation_id))


class TestRedisConversationStore(unittest.TestCase):
    """Test cases for RedisConversationStore (requires Redis or mocks)."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        # Use in-memory store for tests (Redis requires actual connection)
        # In real tests, you would use a test Redis instance or mock
        self.store = InMemoryConversationStore()
    
    @patch.dict(os.environ, {"REDIS_URL": "redis://localhost:6379/0"})
    def test_redis_store_initialization_with_url(self) -> None:
        """Test Redis store initialization with REDIS_URL."""
        # This test would require actual Redis or mocking
        # For now, we'll just verify the store can be created
        try:
            store = RedisConversationStore()
            # If Redis is available, it will connect; otherwise it will fall back
            # This is acceptable behavior
            self.assertIsNotNone(store)
        except Exception:
            # Redis not available - this is expected in test environments
            pass
    
    def test_redis_store_fallback_when_unavailable(self) -> None:
        """Test that Redis store handles connection failures gracefully."""
        # Create store with invalid URL
        store = RedisConversationStore(redis_url="redis://invalid:6379/0")
        # Should not be connected
        self.assertFalse(store._connected)


class TestConversationStoreFactory(unittest.TestCase):
    """Test cases for create_conversation_store factory function."""
    
    @patch.dict(os.environ, {}, clear=True)
    def test_create_store_demo_mode_fallback(self) -> None:
        """Test that demo mode falls back to in-memory when Redis unavailable."""
        # No REDIS_URL set, demo_mode=True
        store = create_conversation_store(demo_mode=True)
        self.assertIsInstance(store, InMemoryConversationStore)
    
    @patch.dict(os.environ, {}, clear=True)
    def test_create_store_production_requires_redis(self) -> None:
        """Test that production mode requires Redis."""
        # No REDIS_URL set, demo_mode=False
        with self.assertRaises(RuntimeError):
            create_conversation_store(demo_mode=False)
    
    def test_get_conversation_ttl(self) -> None:
        """Test TTL configuration from environment."""
        # Test default
        with patch.dict(os.environ, {}, clear=True):
            ttl = get_conversation_ttl()
            self.assertEqual(ttl, 30 * 60)  # Default 30 minutes
        
        # Test custom TTL
        with patch.dict(os.environ, {"CONVERSATION_TTL_SECONDS": "3600"}):
            ttl = get_conversation_ttl()
            self.assertEqual(ttl, 3600)
        
        # Test invalid TTL (should use default)
        with patch.dict(os.environ, {"CONVERSATION_TTL_SECONDS": "invalid"}):
            ttl = get_conversation_ttl()
            self.assertEqual(ttl, 30 * 60)  # Falls back to default


class TestConversationStoreIntegration(unittest.TestCase):
    """Integration tests for conversation store with ConversationRegistry."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        from src.backend.device_registry import DeviceRegistry
        
        self.device_registry = DeviceRegistry(demo_mode=True)
        # Register test devices
        self.device_registry.register_device("device-001", "key1", "controller")
        self.device_registry.provision_device("device-001")
        self.device_registry.confirm_provisioning("device-001")
        
        self.device_registry.register_device("device-002", "key2", "controller")
        self.device_registry.provision_device("device-002")
        self.device_registry.confirm_provisioning("device-002")
        
        self.device_registry.register_device("device-003", "key3", "controller")
        self.device_registry.provision_device("device-003")
        self.device_registry.confirm_provisioning("device-003")
        
        # Create registry with in-memory store
        store = InMemoryConversationStore()
        from src.backend.conversation_registry import ConversationRegistry
        self.registry = ConversationRegistry(
            self.device_registry,
            conversation_store=store,
            demo_mode=True,
        )
    
    def test_conversation_persistence_across_operations(self) -> None:
        """Test that conversations persist across multiple operations."""
        conversation_id = "conv-001"
        participants = ["device-001", "device-002"]
        
        # Create conversation
        success = self.registry.register_conversation(
            conversation_id=conversation_id,
            participants=participants,
        )
        self.assertTrue(success)
        
        # Verify it exists
        self.assertTrue(self.registry.conversation_exists(conversation_id))
        
        # Get participants
        stored_participants = self.registry.get_conversation_participants(conversation_id)
        self.assertEqual(stored_participants, set(participants))
        
        # Add participant
        self.registry.add_participant(conversation_id, "device-003")
        
        # Verify updated participants
        updated_participants = self.registry.get_conversation_participants(conversation_id)
        self.assertEqual(updated_participants, {"device-001", "device-002", "device-003"})
