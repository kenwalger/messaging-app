"""
Identity enforcement service for Abiqua Asset Management.

Implements server-side identity enforcement per:
- Identity Provisioning (#11)
- Functional Specification (#6), Section 3.2
- State Machines (#7), Section 5
- Resolved Specs & Clarifications

This module handles:
- Server-side permission enforcement (client behavior is advisory only)
- Revocation behavior enforcement
- Message sending restrictions
- Conversation creation/join restrictions
- Neutral enterprise mode support
"""

import logging
from typing import Any, Callable, Dict, Optional, Protocol

from src.backend.device_registry import DeviceRegistry

# Configure logging per Logging & Observability (#14)
# Note: No device keys or sensitive data logged per Data Classification (#8)
logger = logging.getLogger(__name__)


class IdentityEnforcementService:
    """
    Identity enforcement service per Functional Spec (#6), Section 3.2.
    
    Enforces device identity-based permissions server-side.
    Client behavior is advisory only; all enforcement is server-side per Resolved Clarifications.
    """
    
    def __init__(self, device_registry: DeviceRegistry) -> None:
        """
        Initialize identity enforcement service.
        
        Args:
            device_registry: Device registry for identity state checks.
        """
        self.device_registry = device_registry
    
    def enforce_message_sending(
        self,
        sender_id: str,
    ) -> Dict[str, Any]:
        """
        Enforce message sending permissions per Functional Spec (#6), Section 4.2.
        
        Server-side enforcement: Only Active devices can send messages.
        Revoked devices cannot send messages per Resolved Clarifications (#38).
        
        Args:
            sender_id: Device ID attempting to send message.
        
        Returns:
            Dictionary with 'allowed' (bool) and 'error_code' (int, if not allowed).
        """
        if not self.device_registry.can_send_messages(sender_id):
            device = self.device_registry.get_device_identity(sender_id)
            if device is None:
                logger.warning(f"Unknown device {sender_id} attempted to send message")
                return {
                    "allowed": False,
                    "error_code": 401,  # Unauthorized
                    "message": "Device not authorized",
                }
            elif device.is_revoked():
                logger.warning(f"Revoked device {sender_id} attempted to send message")
                return {
                    "allowed": False,
                    "error_code": 403,  # Forbidden
                    "message": "Device not authorized",
                }
            else:
                logger.warning(f"Non-active device {sender_id} attempted to send message")
                return {
                    "allowed": False,
                    "error_code": 401,  # Unauthorized
                    "message": "Device not authorized",
                }
        
        return {"allowed": True}
    
    def enforce_conversation_creation(
        self,
        device_id: str,
    ) -> Dict[str, Any]:
        """
        Enforce conversation creation permissions per Functional Spec (#6), Section 4.1.
        
        Server-side enforcement: Only Active devices can create conversations.
        Revoked devices cannot create conversations per Resolved Clarifications (#38).
        
        Args:
            device_id: Device ID attempting to create conversation.
        
        Returns:
            Dictionary with 'allowed' (bool) and 'error_code' (int, if not allowed).
        """
        if not self.device_registry.can_create_conversations(device_id):
            device = self.device_registry.get_device_identity(device_id)
            if device is None:
                logger.warning(f"Unknown device {device_id} attempted to create conversation")
                return {
                    "allowed": False,
                    "error_code": 401,  # Unauthorized
                    "message": "Device not authorized",
                }
            elif device.is_revoked():
                logger.warning(f"Revoked device {device_id} attempted to create conversation")
                return {
                    "allowed": False,
                    "error_code": 403,  # Forbidden
                    "message": "Device not authorized",
                }
            else:
                logger.warning(f"Non-active device {device_id} attempted to create conversation")
                return {
                    "allowed": False,
                    "error_code": 401,  # Unauthorized
                    "message": "Device not authorized",
                }
        
        return {"allowed": True}
    
    def enforce_conversation_join(
        self,
        device_id: str,
    ) -> Dict[str, Any]:
        """
        Enforce conversation join permissions per State Machines (#7), Section 4.
        
        Server-side enforcement: Only Active devices can join conversations.
        Revoked devices cannot join conversations per Resolved Clarifications (#38).
        
        Args:
            device_id: Device ID attempting to join conversation.
        
        Returns:
            Dictionary with 'allowed' (bool) and 'error_code' (int, if not allowed).
        """
        if not self.device_registry.can_join_conversations(device_id):
            device = self.device_registry.get_device_identity(device_id)
            if device is None:
                logger.warning(f"Unknown device {device_id} attempted to join conversation")
                return {
                    "allowed": False,
                    "error_code": 401,  # Unauthorized
                    "message": "Device not authorized",
                }
            elif device.is_revoked():
                logger.warning(f"Revoked device {device_id} attempted to join conversation")
                return {
                    "allowed": False,
                    "error_code": 403,  # Forbidden
                    "message": "Device not authorized",
                }
            else:
                logger.warning(f"Non-active device {device_id} attempted to join conversation")
                return {
                    "allowed": False,
                    "error_code": 401,  # Unauthorized
                    "message": "Device not authorized",
                }
        
        return {"allowed": True}
    
    def enforce_conversation_read(
        self,
        device_id: str,
    ) -> Dict[str, Any]:
        """
        Enforce conversation read permissions per Resolved Clarifications (#38).
        
        Active devices can read conversations.
        Revoked devices can read historical conversations (neutral enterprise mode).
        
        Args:
            device_id: Device ID attempting to read conversation.
        
        Returns:
            Dictionary with 'allowed' (bool) and 'error_code' (int, if not allowed).
        """
        if not self.device_registry.can_read_conversations(device_id):
            logger.warning(f"Device {device_id} not authorized to read conversations")
            return {
                "allowed": False,
                "error_code": 401,  # Unauthorized
                "message": "Device not authorized",
            }
        
        return {"allowed": True}
    
    def handle_revocation_impact(
        self,
        device_id: str,
        conversation_registry: Any,  # ConversationRegistry
    ) -> Dict[str, Any]:
        """
        Handle revocation impact on conversations per State Machines (#7), Section 4.
        
        When a device is revoked:
        - Removed from all conversations
        - Conversations close if all participants revoked
        - Device can still read historical conversations (neutral enterprise mode)
        
        Args:
            device_id: Revoked device identifier.
            conversation_registry: Conversation registry for participant removal.
        
        Returns:
            Dictionary with 'affected_conversations' (list) and 'conversations_closed' (int).
        """
        # Remove revoked device from all conversations per State Machines (#7), Section 4
        affected_conversations = conversation_registry.handle_participant_revocation(device_id)
        
        logger.info(
            f"Revocation impact: Device {device_id} removed from {len(affected_conversations)} conversations"
        )
        
        return {
            "affected_conversations": affected_conversations,
            "conversations_closed": len([
                cid for cid in affected_conversations
                if not conversation_registry.is_conversation_active(cid)
            ]),
        }
