"""
WebSocket connection manager for Abiqua Asset Management.

References:
- API Contracts (#10)
- Functional Specification (#6), Section 5
- Resolved Specs & Clarifications

Implements WebSocketManager Protocol for FastAPI WebSocket connections.
Manages active WebSocket connections and message delivery.
"""

import asyncio
import json
import logging
from collections import deque
from typing import Dict, Optional, Tuple

from fastapi import WebSocket, WebSocketDisconnect

# Configure logging per Logging & Observability (#14)
logger = logging.getLogger(__name__)


class FastAPIWebSocketManager:
    """
    WebSocket connection manager implementation for FastAPI.
    
    Implements WebSocketManager Protocol per message_relay.py.
    Manages active WebSocket connections per device_id.
    
    Uses a message queue and background task to handle sync/async compatibility.
    """
    
    def __init__(self) -> None:
        """
        Initialize WebSocket manager.
        
        Maintains active connections: device_id -> WebSocket instance.
        Uses a queue for message delivery to handle sync/async compatibility.
        """
        # Active WebSocket connections per device_id
        # Classification: Restricted (metadata only) per Data Classification (#8)
        self._connections: Dict[str, WebSocket] = {}
        
        # Message queue for sync/async compatibility
        # Format: (device_id, message) tuples
        self._message_queue: deque[Tuple[str, str]] = deque()
        
        # Background task for processing message queue
        self._send_task: Optional[asyncio.Task] = None
        
        # Event loop reference (set when background task starts)
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
    
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
        
        Queues message for async delivery via background task.
        This allows sync Protocol methods to work with async WebSocket operations.
        
        Args:
            device_id: Target device identifier.
            message: JSON-encoded message string.
        
        Returns:
            True if message queued for sending, False if device not connected.
        """
        # Check if device is connected
        if device_id not in self._connections:
            return False
        
        # Queue message for async delivery
        self._message_queue.append((device_id, message))
        
        # Wake up background task if it exists
        if self._event_loop and self._event_loop.is_running():
            # Schedule wake-up of background task
            try:
                self._event_loop.call_soon_threadsafe(lambda: None)
            except Exception:
                pass  # Event loop may be shutting down
        
        return True
    
    async def _process_message_queue(self) -> None:
        """
        Background task that processes message queue and sends messages asynchronously.
        
        Runs continuously, sending queued messages via WebSocket.
        """
        while True:
            try:
                # Process all queued messages
                while self._message_queue:
                    device_id, message = self._message_queue.popleft()
                    
                    # Check if connection still exists
                    if device_id not in self._connections:
                        continue
                    
                    # Send message asynchronously
                    try:
                        websocket = self._connections[device_id]
                        await websocket.send_text(message)
                        logger.debug(f"Sent WebSocket message to {device_id}")
                    except Exception as e:
                        logger.warning(f"Failed to send WebSocket message to {device_id}: {e}")
                        # Remove connection if send fails
                        self._connections.pop(device_id, None)
                
                # Sleep briefly to avoid busy-waiting
                await asyncio.sleep(0.01)
                
            except asyncio.CancelledError:
                logger.info("WebSocket message queue processor cancelled")
                break
            except Exception as e:
                logger.error(f"Error in WebSocket message queue processor: {e}")
                await asyncio.sleep(0.1)  # Back off on error
    
    def start_background_task(self, event_loop: asyncio.AbstractEventLoop) -> None:
        """
        Start background task for processing message queue.
        
        Should be called during application startup.
        
        Args:
            event_loop: Event loop to run background task in.
        """
        if self._send_task is None or self._send_task.done():
            self._event_loop = event_loop
            self._send_task = event_loop.create_task(self._process_message_queue())
            logger.info("Started WebSocket message queue processor")
    
    def stop_background_task(self) -> None:
        """
        Stop background task for processing message queue.
        
        Should be called during application shutdown.
        """
        if self._send_task and not self._send_task.done():
            self._send_task.cancel()
            logger.info("Stopped WebSocket message queue processor")
    
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
