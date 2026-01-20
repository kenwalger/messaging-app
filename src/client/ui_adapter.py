"""
UI domain adapter layer for Abiqua Asset Management.

References:
- UX Behavior (#12)
- Copy Rules (#13)
- Functional Specification (#6)
- Client-Facing API Boundary (latest)
- Resolved Specs & Clarifications

This module provides adapter functions that map client API DTOs to UI domain models.
All mappings are deterministic and stateless, deriving UX flags from API responses.

No UI rendering, framework-specific code, network calls, or state mutation.
"""

from datetime import datetime
from typing import List, Optional

from src.shared.client_types import (
    ClientConversationDTO,
    ClientConversationState,
    ClientMessageDTO,
    ClientMessageState,
)
from src.shared.message_types import utc_now

from src.client.ui_models import (
    ConversationViewModel,
    DeviceStateViewModel,
    MessageViewModel,
    ParticipantViewModel,
)


class UIAdapter:
    """
    UI domain adapter per UX Behavior (#12) and Copy Rules (#13).
    
    Maps client API DTOs to UI domain models with derived UX flags.
    All mappings are deterministic and stateless.
    """
    
    @staticmethod
    def map_message_to_view_model(
        dto: ClientMessageDTO,
        is_read_only: bool = False,
        current_time: Optional[datetime] = None,
    ) -> MessageViewModel:
        """
        Map ClientMessageDTO to MessageViewModel per UX Behavior (#12), Section 3.3 and 3.4.
        
        Derives UX flags deterministically:
        - is_expired: True if expires_at < current_time
        - is_failed: True if state is FAILED
        - is_read_only: From parameter (neutral enterprise mode)
        
        Args:
            dto: Client-facing message DTO.
            is_read_only: True if device is in neutral enterprise mode (revoked).
            current_time: Optional current time for expiration check (defaults to utc_now()).
        
        Returns:
            MessageViewModel with derived UX flags.
        """
        if current_time is None:
            current_time = utc_now()
        
        # Derive expiration flag deterministically per UX Behavior (#12), Section 3.4
        is_expired = dto.state == ClientMessageState.EXPIRED or dto.expires_at < current_time
        
        # Derive failure flag deterministically per UX Behavior (#12), Section 3.6
        is_failed = dto.state == ClientMessageState.FAILED
        
        return MessageViewModel(
            message_id=dto.message_id,
            sender_id=dto.sender_id,
            conversation_id=dto.conversation_id,
            state=dto.state,
            created_at=dto.created_at,
            expires_at=dto.expires_at,
            is_expired=is_expired,
            is_failed=is_failed,
            is_read_only=is_read_only,
        )
    
    @staticmethod
    def map_conversation_to_view_model(
        dto: ClientConversationDTO,
        is_read_only: bool = False,
    ) -> ConversationViewModel:
        """
        Map ClientConversationDTO to ConversationViewModel per UX Behavior (#12), Section 3.2.
        
        Derives UX flags deterministically:
        - can_send: True if not read-only and conversation is active
        - is_read_only: From parameter (neutral enterprise mode)
        - send_disabled: True if read-only or conversation is closed
        
        Args:
            dto: Client-facing conversation DTO.
            is_read_only: True if device is in neutral enterprise mode (revoked).
        
        Returns:
            ConversationViewModel with derived UX flags.
        """
        # Derive can_send flag per Resolved Clarifications (#38)
        # Revoked devices can read but cannot send/create/join
        can_send = (
            not is_read_only
            and dto.state == ClientConversationState.ACTIVE
        )
        
        # Derive send_disabled flag per UX Behavior (#12), Section 3.2
        # Sending disabled if read-only or conversation is closed
        send_disabled = is_read_only or dto.state == ClientConversationState.CLOSED
        
        return ConversationViewModel(
            conversation_id=dto.conversation_id,
            state=dto.state,
            participant_count=dto.participant_count,
            last_message_at=dto.last_message_at,
            created_at=dto.created_at,
            can_send=can_send,
            is_read_only=is_read_only,
            send_disabled=send_disabled,
        )
    
    @staticmethod
    def map_participant_to_view_model(
        device_id: str,
        display_name: Optional[str] = None,
    ) -> ParticipantViewModel:
        """
        Map participant data to ParticipantViewModel per UX Behavior (#12), Section 3.2.
        
        Args:
            device_id: Device ID (client-visible).
            display_name: Optional display name for UI rendering.
        
        Returns:
            ParticipantViewModel for UI display.
        """
        return ParticipantViewModel(
            device_id=device_id,
            display_name=display_name,
        )
    
    @staticmethod
    def map_device_state_to_view_model(
        device_id: str,
        is_read_only: bool = False,
    ) -> DeviceStateViewModel:
        """
        Map device state to DeviceStateViewModel per UX Behavior (#12), Section 3.1 and 3.5.
        
        Derives UX flags deterministically per Resolved Clarifications (#38):
        - can_send: True if not read-only
        - can_create_conversations: True if not read-only
        - can_join_conversations: True if not read-only
        
        Args:
            device_id: Device ID (client-visible).
            is_read_only: True if device is in neutral enterprise mode (revoked).
        
        Returns:
            DeviceStateViewModel with derived UX flags.
        """
        # Derive permission flags per Resolved Clarifications (#38)
        # Revoked devices can read but cannot send/create/join
        can_send = not is_read_only
        can_create_conversations = not is_read_only
        can_join_conversations = not is_read_only
        
        return DeviceStateViewModel(
            device_id=device_id,
            is_read_only=is_read_only,
            can_send=can_send,
            can_create_conversations=can_create_conversations,
            can_join_conversations=can_join_conversations,
        )
    
    @staticmethod
    def sort_messages_reverse_chronological(
        messages: List[MessageViewModel],
    ) -> List[MessageViewModel]:
        """
        Sort messages in reverse chronological order per Resolved Clarifications (#53).
        
        Newest first: messages sorted by created_at descending.
        
        Args:
            messages: List of message view models to sort.
        
        Returns:
            Sorted list of message view models (newest first).
        """
        return sorted(messages, key=lambda m: m.created_at, reverse=True)
    
    @staticmethod
    def sort_conversations_reverse_chronological(
        conversations: List[ConversationViewModel],
    ) -> List[ConversationViewModel]:
        """
        Sort conversations in reverse chronological order per Resolved Clarifications (#53).
        
        Newest first: conversations sorted by sort_key (last_message_at or created_at) descending.
        
        Args:
            conversations: List of conversation view models to sort.
        
        Returns:
            Sorted list of conversation view models (newest first).
        """
        return sorted(conversations, key=lambda c: c.sort_key, reverse=True)
    
    @staticmethod
    def filter_expired_messages(
        messages: List[MessageViewModel],
        current_time: Optional[datetime] = None,
    ) -> List[MessageViewModel]:
        """
        Filter out expired messages per UX Behavior (#12), Section 3.4.
        
        Expired messages are removed automatically; no undo per UX Behavior (#12), Section 3.3.
        
        Args:
            messages: List of message view models to filter.
            current_time: Optional current time for expiration check (defaults to utc_now()).
        
        Returns:
            List of non-expired message view models.
        """
        if current_time is None:
            current_time = utc_now()
        
        return [msg for msg in messages if not msg.is_expired]
    
    @staticmethod
    def filter_failed_messages(
        messages: List[MessageViewModel],
    ) -> List[MessageViewModel]:
        """
        Filter failed messages for display per UX Behavior (#12), Section 3.6.
        
        Failed messages are explicitly distinguishable per deterministic rules.
        
        Args:
            messages: List of message view models to filter.
        
        Returns:
            List of failed message view models.
        """
        return [msg for msg in messages if msg.is_failed]
    
    @staticmethod
    def filter_active_conversations(
        conversations: List[ConversationViewModel],
    ) -> List[ConversationViewModel]:
        """
        Filter active conversations per UX Behavior (#12), Section 3.2.
        
        Display active conversations only per UX Behavior (#12), Section 3.2.
        
        Args:
            conversations: List of conversation view models to filter.
        
        Returns:
            List of active conversation view models.
        """
        return [
            conv for conv in conversations
            if conv.state == ClientConversationState.ACTIVE
        ]
