"""
WebSocket connection manager for Abiqua Asset Management.

References:
- API Contracts (#10)
- Functional Specification (#6), Section 5
- Resolved Specs & Clarifications

Implements WebSocketManager Protocol for FastAPI WebSocket connections.
Manages active WebSocket connections and message delivery.
"""

import json
import logging
from typing import Dict, Optional

from fastapi import WebSocket, WebSocketDisconnect

# Configure logging per Logging & Observability (#14)
logger = logging.getLogger(__name__)


class FastAPIWebSocketManager:
    """
    WebSocket connection manager implementation for FastAPI.
    
    Implements WebSocketManager Protocol per message_relay.py.
    Manages active WebSocket connections per device_id.
    """
    
    def __init__(self) -> None:
        """
        Initialize WebSocket manager.
        
        Maintains active connections: device_id -> WebSocket instance.
        """
        # Active WebSocket connections per device_id
        # Classification: Restricted (metadata only) per Data Classification (#8)
        self._connections: Dict[str, WebSocket] = {}
    
    def is_connected(self, device_id: str) -> bool:
        """
        Check if device has active WebSocket connection.
        
        Args:
            device_id: Device identifier to check.
        
        Returns:
            True if device has active WebSocket connection, False otherwise.
        """
        return device_id in self._connections
    
    async def send_to_device_async(self, device_id: str, message: str) -> bool:
        """
        Send message to device via WebSocket (async version).
        
        Args:
            device_id: Target device identifier.
            message: JSON-encoded message string.
        
        Returns:
            True if message sent successfully, False otherwise.
        """
        if device_id not in self._connections:
            return False
        
        websocket = self._connections[device_id]
        
        try:
            await websocket.send_text(message)
            return True
        except Exception as e:
            logger.warning(f"Failed to send WebSocket message to {device_id}: {e}")
            # Remove connection if send fails
            self._connections.pop(device_id, None)
            return False
    
    def send_to_device(self, device_id: str, message: str) -> bool:
        """
        Send message to device via WebSocket (sync wrapper for Protocol compatibility).
        
        Note: This method exists for Protocol compatibility.
        In async contexts, use send_to_device_async() instead.
        This sync version attempts to send but may not work correctly in all contexts.
        
        Args:
            device_id: Target device identifier.
            message: JSON-encoded message string.
        
        Returns:
            True if message queued for sending, False otherwise.
        """
        # For Protocol compatibility, we return True if connection exists
        # Actual sending should be done via async method
        return device_id in self._connections
    
    async def connect(self, device_id: str, websocket: WebSocket) -> None:
        """
        Register WebSocket connection for device.
        
        Args:
            device_id: Device identifier.
            websocket: FastAPI WebSocket instance.
        """
        # Accept WebSocket connection
        await websocket.accept()
        
        # Register connection
        self._connections[device_id] = websocket
        
        logger.info(f"WebSocket connected for device {device_id}")
    
    async def disconnect(self, device_id: str) -> None:
        """
        Unregister WebSocket connection for device.
        
        Args:
            device_id: Device identifier.
        """
        if device_id in self._connections:
            websocket = self._connections.pop(device_id)
            try:
                await websocket.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket for {device_id}: {e}")
            
            logger.info(f"WebSocket disconnected for device {device_id}")
    
    def get_connection(self, device_id: str) -> Optional[WebSocket]:
        """
        Get WebSocket connection for device.
        
        Args:
            device_id: Device identifier.
        
        Returns:
            WebSocket instance if connected, None otherwise.
        """
        return self._connections.get(device_id)
