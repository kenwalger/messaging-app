"""
Backend conversation API service for Abiqua Asset Management.

Implements conversation management API endpoints per:
- Functional Specification (#6), Section 4.1
- State Machines (#7), Section 4
- API Contracts (#10)
- Identity Provisioning (#11)
- Resolved Specs & Clarifications

This module handles:
- Conversation creation with permission enforcement
- Participant join/leave operations
- Conversation closure
- Permission validation (only provisioned devices)
- Max group size enforcement (50 participants)
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol
from uuid import uuid4

from src.shared.constants import HEADER_DEVICE_ID, MAX_GROUP_SIZE
from src.shared.conversation_types import Conversation, ConversationState
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


class ConversationService:
    """
    Backend conversation API service per Functional Spec (#6), Section 4.1 and State Machines (#7), Section 4.
    
    Handles conversation lifecycle management with permission enforcement.
    Only provisioned devices (Active state) may create or join conversations per Identity Provisioning (#11).
    """
    
    def __init__(
        self,
        conversation_registry: Any,  # ConversationRegistry from conversation_registry.py
        device_registry: DeviceRegistry,
        log_service: Optional[Any] = None,  # LogService Protocol
    ) -> None:
        """
        Initialize conversation API service.
        
        Args:
            conversation_registry: Conversation registry for membership tracking.
            device_registry: Device registry for permission validation.
            log_service: Optional logging service for operational events per
                Logging & Observability (#14).
        """
        self.conversation_registry = conversation_registry
        self.device_registry = device_registry
        self.log_service = log_service
    
    def create_conversation(
        self,
        device_id: str,
        participants: List[str],
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create conversation API endpoint per Functional Spec (#6), Section 4.1 and State Machines (#7), Section 4.
        
        Endpoint: POST /api/conversation/create
        Permission: Only provisioned devices (Active state) may create conversations per Identity Provisioning (#11).
        
        Transitions: Uncreated -> Active per State Machines (#7), Section 4.
        
        Args:
            device_id: Device ID creating the conversation (from X-Device-ID header).
            participants: List of participant device IDs (max 50 per Resolved TBDs).
            conversation_id: Optional conversation identifier. If None, generates UUID v4.
        
        Returns:
            Response dictionary with status and conversation_id.
            Status codes: 200 (success), 400 (invalid request), 401 (unauthorized device), 403 (revoked device).
        
        Raises:
            ValueError: If constraints violated (group size, empty participants).
        """
        # Permission check: Only provisioned devices may create conversations per Identity Provisioning (#11)
        if not self.device_registry.is_device_active(device_id):
            logger.warning(f"Revoked or invalid device {device_id} attempted to create conversation")
            return {
                "status": "error",
                "error_code": 403,
                "message": "Device not authorized",
            }
        
        # Validate participants list
        if not participants:
            return {
                "status": "error",
                "error_code": 400,
                "message": "Conversation must have at least one participant",
            }
        
        # Ensure creator is included in participants
        if device_id not in participants:
            participants = [device_id] + participants
        
        # Validate group size per Resolved TBDs
        if len(participants) > MAX_GROUP_SIZE:
            return {
                "status": "error",
                "error_code": 400,
                "message": f"Participants exceed max group size of {MAX_GROUP_SIZE}",
            }
        
        # Validate all participants are provisioned per Identity Provisioning (#11)
        invalid_participants = [
            pid for pid in participants
            if not self.device_registry.is_device_active(pid)
        ]
        if invalid_participants:
            logger.warning(f"Invalid participants in conversation creation: {invalid_participants}")
            return {
                "status": "error",
                "error_code": 400,
                "message": "All participants must be provisioned devices",
            }
        
        # Generate conversation ID if not provided
        if conversation_id is None:
            conversation_id = str(uuid4())
        
        # Defensive error handling: Check if conversation already exists with this ID
        if self.conversation_registry.conversation_exists(conversation_id):
            # Conversation with this ID already exists - return it
            existing_participants = self.conversation_registry.get_conversation_participants(conversation_id)
            if self.conversation_registry.is_conversation_active(conversation_id):
                logger.info(f"Conversation {conversation_id} already exists, returning existing conversation")
                return {
                    "status": "success",
                    "conversation_id": conversation_id,
                    "participants": list(existing_participants),
                    "status_code": 200,
                }
            else:
                # Conversation exists but is closed - return error
                return {
                    "status": "error",
                    "error_code": 400,
                    "message": "Conversation exists but is closed",
                    "status_code": 400,
                }
        
        # Register conversation in registry per Functional Spec (#6), Section 4.1
        success = self.conversation_registry.register_conversation(
            conversation_id=conversation_id,
            participants=participants,
        )
        
        if not success:
            return {
                "status": "error",
                "error_code": 400,
                "message": "Failed to create conversation",
                "status_code": 400,
            }
        
        # Log conversation creation per Logging & Observability (#14)
        # Use string for now since conversation_created is not in LogEventType enum
        # The logging service now handles strings gracefully
        if self.log_service:
            self.log_service.log_event(
                "conversation_created",  # String - logging service will handle it
                {
                    "conversation_id": conversation_id,
                    "created_by": device_id,
                    "participant_count": len(participants),
                    "timestamp": utc_now().isoformat(),
                },
            )
        
        logger.info(f"Conversation {conversation_id} created by device {device_id}")
        
        return {
            "status": "success",
            "conversation_id": conversation_id,
            "participants": participants,
            "state": ConversationState.ACTIVE.value,
        }
    
    def join_conversation(
        self,
        device_id: str,
        conversation_id: str,
    ) -> Dict[str, Any]:
        """
        Join conversation API endpoint per State Machines (#7), Section 4.
        
        Endpoint: POST /api/conversation/join
        Permission: Only provisioned devices (Active state) may join conversations per Identity Provisioning (#11).
        
        Args:
            device_id: Device ID joining the conversation (from X-Device-ID header).
            conversation_id: Conversation identifier to join.
        
        Returns:
            Response dictionary with status.
            Status codes: 200 (success), 400 (invalid request), 401 (unauthorized device), 403 (revoked device), 404 (conversation not found).
        """
        # Permission check: Only provisioned devices may join conversations per Identity Provisioning (#11)
        if not self.device_registry.is_device_active(device_id):
            logger.warning(f"Revoked or invalid device {device_id} attempted to join conversation")
            return {
                "status": "error",
                "error_code": 403,
                "message": "Device not authorized",
            }
        
        # Check if conversation exists and is active
        conversation_exists = self.conversation_registry.conversation_exists(conversation_id)
        is_active = self.conversation_registry.is_conversation_active(conversation_id)
        
        # In demo mode: Auto-create conversation if it doesn't exist (for multi-device demos)
        # This handles cases where conversation was created on a different dyno or lost due to restart
        demo_mode = getattr(self.device_registry, '_demo_mode', False)
        if not conversation_exists and demo_mode:
            logger.warning(f"[DEMO MODE] Auto-creating conversation {conversation_id} for device {device_id} (conversation_not_found)")
            # Create conversation with the joining device as the first participant
            success = self.conversation_registry.register_conversation(
                conversation_id=conversation_id,
                participants=[device_id],
            )
            if success:
                logger.info(f"[DEMO MODE] Successfully auto-created conversation {conversation_id}")
                # Log event for observability
                if self.log_service:
                    self.log_service.log_event(
                        "demo_mode_auto_create",
                        {
                            "conversation_id": conversation_id,
                            "device_id": device_id,
                            "reason": "conversation_not_found",
                        },
                    )
            else:
                logger.warning(f"[DEMO MODE] Failed to auto-create conversation {conversation_id} (may have been created by another request)")
                # Re-check existence in case it was created by another request
                conversation_exists = self.conversation_registry.conversation_exists(conversation_id)
                is_active = self.conversation_registry.is_conversation_active(conversation_id)
        elif not is_active:
            return {
                "status": "error",
                "error_code": 404,
                "message": "Conversation not found or closed",
            }
        
        # Check if already a participant
        participants = self.conversation_registry.get_conversation_participants(conversation_id)
        if participants and device_id in participants:
            return {
                "status": "success",
                "message": "Already a participant",
                "conversation_id": conversation_id,
            }
        
        # Check group size limit before attempting to add per Resolved TBDs
        if participants and len(participants) >= MAX_GROUP_SIZE:
            return {
                "status": "error",
                "error_code": 400,
                "message": f"Conversation has reached max group size of {MAX_GROUP_SIZE}",
            }
        
        # Add participant per State Machines (#7), Section 4
        success = self.conversation_registry.add_participant(
            conversation_id=conversation_id,
            device_id=device_id,
        )
        
        if not success:
            return {
                "status": "error",
                "error_code": 400,
                "message": "Failed to join conversation",
            }
        
        # Log participant join per Logging & Observability (#14)
        if self.log_service:
            self.log_service.log_event(
                "conversation_participant_joined",
                {
                    "conversation_id": conversation_id,
                    "device_id": device_id,
                    "timestamp": utc_now().isoformat(),
                },
            )
        
        logger.info(f"Device {device_id} joined conversation {conversation_id}")
        
        return {
            "status": "success",
            "conversation_id": conversation_id,
            "message": "Successfully joined conversation",
        }
    
    def leave_conversation(
        self,
        device_id: str,
        conversation_id: str,
    ) -> Dict[str, Any]:
        """
        Leave conversation API endpoint per State Machines (#7), Section 4.
        
        Endpoint: POST /api/conversation/leave
        Permission: Any participant may leave a conversation.
        
        If all participants leave, conversation transitions to Closed state per State Machines (#7), Section 4.
        
        Args:
            device_id: Device ID leaving the conversation (from X-Device-ID header).
            conversation_id: Conversation identifier to leave.
        
        Returns:
            Response dictionary with status.
            Status codes: 200 (success), 404 (conversation not found or not a participant).
        """
        # Check if conversation exists
        participants = self.conversation_registry.get_conversation_participants(conversation_id)
        if not participants:
            return {
                "status": "error",
                "error_code": 404,
                "message": "Conversation not found",
            }
        
        # Check if device is a participant
        if device_id not in participants:
            return {
                "status": "error",
                "error_code": 404,
                "message": "Not a participant in this conversation",
            }
        
        # Remove participant per State Machines (#7), Section 4
        success = self.conversation_registry.remove_participant(
            conversation_id=conversation_id,
            device_id=device_id,
        )
        
        if not success:
            return {
                "status": "error",
                "error_code": 400,
                "message": "Failed to leave conversation",
            }
        
        # Check if conversation was closed (all participants left)
        is_closed = not self.conversation_registry.is_conversation_active(conversation_id)
        
        # Log participant leave per Logging & Observability (#14)
        if self.log_service:
            self.log_service.log_event(
                "conversation_participant_left",
                {
                    "conversation_id": conversation_id,
                    "device_id": device_id,
                    "conversation_closed": is_closed,
                    "timestamp": utc_now().isoformat(),
                },
            )
        
        logger.info(f"Device {device_id} left conversation {conversation_id}")
        
        response = {
            "status": "success",
            "conversation_id": conversation_id,
            "message": "Successfully left conversation",
        }
        
        if is_closed:
            response["conversation_closed"] = True
            response["message"] = "Left conversation; conversation closed (no participants remaining)"
        
        return response
    
    def close_conversation(
        self,
        device_id: str,
        conversation_id: str,
    ) -> Dict[str, Any]:
        """
        Close conversation API endpoint per State Machines (#7), Section 4.
        
        Endpoint: POST /api/conversation/close
        Permission: Only participants may close a conversation.
        
        Transitions: Active -> Closed per State Machines (#7), Section 4.
        All messages in closed conversation remain until expiration per Resolved Clarifications (#36).
        No new messages accepted in closed conversations per Resolved Clarifications (#36).
        
        Args:
            device_id: Device ID closing the conversation (from X-Device-ID header).
            conversation_id: Conversation identifier to close.
        
        Returns:
            Response dictionary with status.
            Status codes: 200 (success), 403 (not a participant), 404 (conversation not found).
        """
        # Check if conversation exists
        participants = self.conversation_registry.get_conversation_participants(conversation_id)
        if not participants:
            return {
                "status": "error",
                "error_code": 404,
                "message": "Conversation not found",
            }
        
        # Permission check: Only participants may close conversation
        if device_id not in participants:
            return {
                "status": "error",
                "error_code": 403,
                "message": "Not a participant in this conversation",
            }
        
        # Check if already closed
        if not self.conversation_registry.is_conversation_active(conversation_id):
            return {
                "status": "success",
                "message": "Conversation already closed",
                "conversation_id": conversation_id,
            }
        
        # Close conversation per State Machines (#7), Section 4
        success = self.conversation_registry.close_conversation(conversation_id)
        
        if not success:
            return {
                "status": "error",
                "error_code": 400,
                "message": "Failed to close conversation",
            }
        
        # Log conversation closure per Logging & Observability (#14)
        if self.log_service:
            self.log_service.log_event(
                "conversation_closed",
                {
                    "conversation_id": conversation_id,
                    "closed_by": device_id,
                    "timestamp": utc_now().isoformat(),
                },
            )
        
        logger.info(f"Conversation {conversation_id} closed by device {device_id}")
        
        return {
            "status": "success",
            "conversation_id": conversation_id,
            "message": "Conversation closed successfully",
            "state": ConversationState.CLOSED.value,
        }
    
    def get_conversation_info(
        self,
        device_id: str,
        conversation_id: str,
    ) -> Dict[str, Any]:
        """
        Get conversation information API endpoint.
        
        Endpoint: GET /api/conversation/info
        Permission: Only participants or revoked devices (neutral enterprise mode) may view conversation info.
        
        Revoked devices can view conversation list per Resolved Clarifications (#38).
        
        Args:
            device_id: Device ID requesting conversation info (from X-Device-ID header).
            conversation_id: Conversation identifier.
        
        Returns:
            Response dictionary with conversation information.
            Status codes: 200 (success), 404 (conversation not found or not a participant).
        """
        # Check if conversation exists
        participants = self.conversation_registry.get_conversation_participants(conversation_id)
        if not participants:
            return {
                "status": "error",
                "error_code": 404,
                "message": "Conversation not found",
            }
        
        # Permission check: Participants or revoked devices (neutral enterprise mode) may view
        # Revoked devices can view conversation list per Resolved Clarifications (#38)
        is_participant = device_id in participants
        is_revoked = not self.device_registry.is_device_active(device_id)
        
        if not is_participant and not is_revoked:
            return {
                "status": "error",
                "error_code": 403,
                "message": "Not authorized to view this conversation",
            }
        
        # Get conversation state
        is_active = self.conversation_registry.is_conversation_active(conversation_id)
        
        return {
            "status": "success",
            "conversation_id": conversation_id,
            "state": ConversationState.ACTIVE.value if is_active else ConversationState.CLOSED.value,
            "participants": list(participants),
            "participant_count": len(participants),
            "is_participant": is_participant,
        }
