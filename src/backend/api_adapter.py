"""
API adapter layer for Abiqua Asset Management.

Implements client-facing API boundary per:
- API Contracts (#10)
- UX Behavior (#12)
- Copy Rules (#13)
- Functional Specification (#6)
- Resolved Specs & Clarifications

This module handles:
- Mapping internal models to client DTOs
- Normalizing errors and states for UI consumption
- Hiding internal implementation details
- API versioning (v1)
"""

import logging
from typing import Any, Dict, List, Optional

from src.shared.client_types import (
    ClientConversationDTO,
    ClientConversationState,
    ClientErrorCode,
    ClientErrorResponse,
    ClientMessageDTO,
    ClientMessageState,
    ClientSuccessResponse,
)
from src.shared.constants import (
    ERROR_BACKEND_UNREACHABLE,
    ERROR_EMPTY_MESSAGE,
    ERROR_MESSAGING_DISABLED,
    ERROR_NETWORK_UNAVAILABLE,
)
from src.shared.conversation_types import Conversation, ConversationState
from src.shared.device_identity_types import DeviceIdentityState
from src.shared.message_types import Message, MessageState

# Configure logging per Logging & Observability (#14)
logger = logging.getLogger(__name__)

# API version per API Contracts (#10)
API_VERSION = "v1"


class APIAdapter:
    """
    API adapter layer per API Contracts (#10) and UX Behavior (#12).
    
    Maps internal models to client-safe DTOs, hiding:
    - Internal state machine names
    - Retry counters
    - Cryptographic material
    - Internal error stacks
    
    All responses are versioned (v1) per API Contracts (#10).
    """
    
    @staticmethod
    def map_message_to_dto(message: Message) -> ClientMessageDTO:
        """
        Map internal Message to client DTO per UX Behavior (#12), Section 4.
        
        Hides internal state machine details and retry counters.
        Maps internal states to client-visible states.
        
        Args:
            message: Internal Message object.
        
        Returns:
            ClientMessageDTO with client-safe state.
        """
        # Map internal state to client-visible state per UX Behavior (#12), Section 4
        client_state = APIAdapter._map_message_state(message.state)
        
        return ClientMessageDTO(
            message_id=str(message.message_id),
            sender_id=message.sender_id,
            conversation_id=message.conversation_id,
            state=client_state,
            created_at=message.creation_timestamp,
            expires_at=message.expiration_timestamp,
        )
    
    @staticmethod
    def _map_message_state(internal_state: MessageState) -> ClientMessageState:
        """
        Map internal message state to client-visible state per UX Behavior (#12), Section 4.
        
        Clients never see: PendingDelivery, retry_count, or internal state names.
        
        Args:
            internal_state: Internal MessageState enum value.
        
        Returns:
            ClientMessageState enum value.
        """
        mapping = {
            MessageState.CREATED: ClientMessageState.SENT,
            MessageState.PENDING_DELIVERY: ClientMessageState.SENT,
            MessageState.DELIVERED: ClientMessageState.DELIVERED,
            MessageState.FAILED: ClientMessageState.FAILED,
            MessageState.ACTIVE: ClientMessageState.DELIVERED,  # Active messages are delivered
            MessageState.EXPIRED: ClientMessageState.EXPIRED,
        }
        
        return mapping.get(internal_state, ClientMessageState.FAILED)
    
    @staticmethod
    def map_conversation_to_dto(conversation: Conversation) -> ClientConversationDTO:
        """
        Map internal Conversation to client DTO per UX Behavior (#12), Section 3.2.
        
        Hides internal state machine details.
        
        Args:
            conversation: Internal Conversation object.
        
        Returns:
            ClientConversationDTO with client-safe state.
        """
        # Map internal state to client-visible state
        client_state = APIAdapter._map_conversation_state(conversation.state)
        
        return ClientConversationDTO(
            conversation_id=str(conversation.conversation_id),
            state=client_state,
            participant_count=len(conversation.participants),
            last_message_at=conversation.last_message_timestamp,
            created_at=conversation.created_at,
        )
    
    @staticmethod
    def _map_conversation_state(internal_state: ConversationState) -> ClientConversationState:
        """
        Map internal conversation state to client-visible state.
        
        Args:
            internal_state: Internal ConversationState enum value.
        
        Returns:
            ClientConversationState enum value.
        """
        mapping = {
            ConversationState.UNCREATED: ClientConversationState.CLOSED,
            ConversationState.ACTIVE: ClientConversationState.ACTIVE,
            ConversationState.CLOSED: ClientConversationState.CLOSED,
        }
        
        return mapping.get(internal_state, ClientConversationState.CLOSED)
    
    @staticmethod
    def map_device_state_to_read_only(device_state: DeviceIdentityState) -> bool:
        """
        Check if device should be in read-only mode per Resolved Clarifications (#38).
        
        Revoked devices can read historical conversations but cannot send/create/join.
        
        Args:
            device_state: Internal DeviceIdentityState enum value.
        
        Returns:
            True if device should be in read-only mode, False otherwise.
        """
        return device_state == DeviceIdentityState.REVOKED
    
    @staticmethod
    def create_error_response(
        error_code: ClientErrorCode,
        message: Optional[str] = None,
    ) -> ClientErrorResponse:
        """
        Create client-facing error response per API Contracts (#10), Section 6 and Copy Rules (#13), Section 4.
        
        Error messages are deterministic and neutral per Copy Rules (#13), Section 4.
        No sensitive information or technical details exposed.
        
        Args:
            error_code: Client-visible error code.
            message: Optional error message (defaults to standard message per Copy Rules).
        
        Returns:
            ClientErrorResponse with neutral error message.
        """
        # Use standard error messages per Copy Rules (#13), Section 4
        if message is None:
            message = APIAdapter._get_standard_error_message(error_code)
        
        return ClientErrorResponse(
            error_code=error_code,
            message=message,
            api_version=API_VERSION,
        )
    
    @staticmethod
    def _get_standard_error_message(error_code: ClientErrorCode) -> str:
        """
        Get standard error message per Copy Rules (#13), Section 4.
        
        Error messages are deterministic and neutral.
        No technical details or sensitive information.
        
        Args:
            error_code: Client-visible error code.
        
        Returns:
            Standard error message string.
        """
        messages = {
            ClientErrorCode.INVALID_REQUEST: ERROR_EMPTY_MESSAGE,  # Default for 400
            ClientErrorCode.UNAUTHORIZED_DEVICE: ERROR_MESSAGING_DISABLED,
            ClientErrorCode.REVOKED_DEVICE: ERROR_MESSAGING_DISABLED,
            ClientErrorCode.RESOURCE_NOT_FOUND: "Resource not found",
            ClientErrorCode.BACKEND_FAILURE: ERROR_BACKEND_UNREACHABLE,
        }
        
        return messages.get(error_code, "An error occurred")
    
    @staticmethod
    def create_success_response(data: Optional[Dict[str, Any]] = None) -> ClientSuccessResponse:
        """
        Create client-facing success response per API Contracts (#10).
        
        Args:
            data: Optional response data dictionary.
        
        Returns:
            ClientSuccessResponse with API versioning.
        """
        return ClientSuccessResponse(
            status="success",
            api_version=API_VERSION,
            data=data,
        )
    
    @staticmethod
    def normalize_backend_error(
        backend_error: Exception,
        default_code: ClientErrorCode = ClientErrorCode.BACKEND_FAILURE,
    ) -> ClientErrorResponse:
        """
        Normalize backend errors to client-safe error responses per Copy Rules (#13), Section 4.
        
        Clients never see:
        - Internal error stacks
        - Technical error details
        - Sensitive information
        
        Args:
            backend_error: Internal exception.
            default_code: Default error code if error type cannot be determined.
        
        Returns:
            ClientErrorResponse with neutral error message.
        """
        # Map common exceptions to error codes
        error_type = type(backend_error).__name__
        
        # Log internal error details (not exposed to client)
        logger.warning(f"Backend error normalized: {error_type} - {str(backend_error)}")
        
        # Return neutral error response (no technical details)
        return APIAdapter.create_error_response(
            error_code=default_code,
            message=APIAdapter._get_standard_error_message(default_code),
        )
    
    @staticmethod
    def create_message_list_response(messages: List[Message]) -> Dict[str, Any]:
        """
        Create client-facing message list response per API Contracts (#10), Section 3.4.
        
        Args:
            messages: List of internal Message objects.
        
        Returns:
            Dictionary with messages array and API version.
        """
        message_dtos = [APIAdapter.map_message_to_dto(msg) for msg in messages]
        
        return {
            "api_version": API_VERSION,
            "messages": [
                {
                    "message_id": dto.message_id,
                    "sender_id": dto.sender_id,
                    "conversation_id": dto.conversation_id,
                    "state": dto.state.value,
                    "created_at": dto.created_at.isoformat(),
                    "expires_at": dto.expires_at.isoformat(),
                }
                for dto in message_dtos
            ],
        }
    
    @staticmethod
    def create_conversation_list_response(conversations: List[Conversation]) -> Dict[str, Any]:
        """
        Create client-facing conversation list response per UX Behavior (#12), Section 3.2.
        
        Args:
            conversations: List of internal Conversation objects.
        
        Returns:
            Dictionary with conversations array and API version.
        """
        conversation_dtos = [APIAdapter.map_conversation_to_dto(conv) for conv in conversations]
        
        return {
            "api_version": API_VERSION,
            "conversations": [
                {
                    "conversation_id": dto.conversation_id,
                    "state": dto.state.value,
                    "participant_count": dto.participant_count,
                    "last_message_at": (
                        dto.last_message_at.isoformat() if dto.last_message_at else None
                    ),
                    "created_at": dto.created_at.isoformat(),
                }
                for dto in conversation_dtos
            ],
        }
