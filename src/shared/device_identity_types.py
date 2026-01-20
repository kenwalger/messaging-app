"""
Device identity types and state enums for Abiqua Asset Management.

References:
- Identity Provisioning (#11)
- State Machines (#7), Section 5
- Functional Specification (#6), Section 3.1
- Resolved Specs & Clarifications
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from src.shared.message_types import utc_now


class DeviceIdentityState(Enum):
    """
    Device identity lifecycle states per State Machines (#7), Section 5.
    
    State transitions:
    Pending → Provisioned → Active → Revoked
    
    Notes:
    - Only Controllers can move devices between states per State Machines (#7)
    - Revocation is immediate and irreversible per Identity Provisioning (#11), Section 5
    - Device revocation triggers key rotation per Resolved Clarifications
    """
    PENDING = "pending"
    PROVISIONED = "provisioned"
    ACTIVE = "active"
    REVOKED = "revoked"


@dataclass
class DeviceIdentity:
    """
    Device identity data structure per Identity Provisioning (#11), Section 2.
    
    Identity is device-bound; each device has exactly one identity.
    Identity consists of device_id, public/private key pair, and provisioning metadata.
    
    Classification: Restricted (Data Classification #8, Section 3)
    """
    device_id: str  # Unique UUID per Identity Provisioning (#11), Section 2
    state: DeviceIdentityState  # Current state per State Machines (#7), Section 5
    public_key: str  # Public key for encryption/authentication
    created_at: datetime = field(default_factory=utc_now)  # Provisioning timestamp
    provisioned_at: Optional[datetime] = None  # When device received provisioning data
    activated_at: Optional[datetime] = None  # When device confirmed provisioning (Active state)
    revoked_at: Optional[datetime] = None  # When device was revoked (Revoked state)
    last_key_rotation: datetime = field(default_factory=utc_now)  # Last key rotation timestamp
    next_key_rotation: Optional[datetime] = None  # Scheduled next rotation (90 days per Resolved TBDs)
    controller_id: Optional[str] = None  # Controller that provisioned this device
    
    def __post_init__(self) -> None:
        """
        Post-initialization for DeviceIdentity.
        
        Sets initial key rotation schedule if not provided.
        """
        if self.next_key_rotation is None:
            # Schedule next rotation 90 days from creation per Resolved TBDs
            from datetime import timedelta
            self.next_key_rotation = self.created_at + timedelta(days=90)
    
    def is_active(self) -> bool:
        """
        Check if device is in Active state per State Machines (#7), Section 5.
        
        Returns:
            True if device is Active, False otherwise.
        """
        return self.state == DeviceIdentityState.ACTIVE
    
    def is_revoked(self) -> bool:
        """
        Check if device is in Revoked state per State Machines (#7), Section 5.
        
        Returns:
            True if device is Revoked, False otherwise.
        """
        return self.state == DeviceIdentityState.REVOKED
    
    def can_send_messages(self) -> bool:
        """
        Check if device can send messages per Functional Spec (#6), Section 4.2.
        
        Only Active devices can send messages.
        Revoked devices cannot send messages per Resolved Clarifications (#38).
        
        Returns:
            True if device is Active, False otherwise.
        """
        return self.is_active()
    
    def can_create_conversations(self) -> bool:
        """
        Check if device can create conversations per Functional Spec (#6), Section 4.1.
        
        Only Active devices can create conversations.
        Revoked devices cannot create conversations per Resolved Clarifications (#38).
        
        Returns:
            True if device is Active, False otherwise.
        """
        return self.is_active()
    
    def can_join_conversations(self) -> bool:
        """
        Check if device can join conversations per State Machines (#7), Section 4.
        
        Only Active devices can join conversations.
        Revoked devices cannot join conversations per Resolved Clarifications (#38).
        
        Returns:
            True if device is Active, False otherwise.
        """
        return self.is_active()
    
    def can_read_conversations(self) -> bool:
        """
        Check if device can read historical conversations per Resolved Clarifications (#38).
        
        Active devices can read conversations.
        Revoked devices can read historical conversations (neutral enterprise mode).
        
        Returns:
            True if device is Active or Revoked, False otherwise.
        """
        return self.is_active() or self.is_revoked()
    
    def needs_key_rotation(self) -> bool:
        """
        Check if device needs key rotation per Resolved TBDs.
        
        Key rotation required:
        - Every 90 days (scheduled rotation)
        - Immediately upon revocation
        
        Returns:
            True if key rotation is needed, False otherwise.
        """
        if self.is_revoked():
            # Revoked devices always need key rotation per Resolved Clarifications
            return True
        
        if self.next_key_rotation is None:
            return False
        
        # Check if scheduled rotation is due
        return utc_now() >= self.next_key_rotation
    
    def transition_to_provisioned(self, timestamp: Optional[datetime] = None) -> None:
        """
        Transition device to Provisioned state per State Machines (#7), Section 5.
        
        Trigger: Controller initiates provisioning
        Action: Device receives provisioning data
        
        Args:
            timestamp: Optional timestamp for provisioning. Defaults to current time.
        """
        if self.state != DeviceIdentityState.PENDING:
            raise ValueError(f"Cannot transition to Provisioned from {self.state.value} state")
        
        self.state = DeviceIdentityState.PROVISIONED
        self.provisioned_at = timestamp or utc_now()
    
    def transition_to_active(self, timestamp: Optional[datetime] = None) -> None:
        """
        Transition device to Active state per State Machines (#7), Section 5.
        
        Trigger: Device confirms provisioning
        Action: Activate device identity; enable messaging features
        
        Args:
            timestamp: Optional timestamp for activation. Defaults to current time.
        """
        if self.state != DeviceIdentityState.PROVISIONED:
            raise ValueError(f"Cannot transition to Active from {self.state.value} state")
        
        self.state = DeviceIdentityState.ACTIVE
        self.activated_at = timestamp or utc_now()
    
    def transition_to_revoked(
        self,
        timestamp: Optional[datetime] = None,
        trigger_key_rotation: bool = True,
    ) -> None:
        """
        Transition device to Revoked state per State Machines (#7), Section 5.
        
        Trigger: Controller revokes device
        Action: Mark identity revoked; trigger key rotation if needed
        
        Revocation is immediate and irreversible per Identity Provisioning (#11), Section 5.
        
        Args:
            timestamp: Optional timestamp for revocation. Defaults to current time.
            trigger_key_rotation: Whether to trigger key rotation (default True per Resolved Clarifications).
        """
        if self.state == DeviceIdentityState.REVOKED:
            # Already revoked, no-op
            return
        
        if self.state not in (DeviceIdentityState.ACTIVE, DeviceIdentityState.PROVISIONED):
            raise ValueError(f"Cannot transition to Revoked from {self.state.value} state")
        
        self.state = DeviceIdentityState.REVOKED
        self.revoked_at = timestamp or utc_now()
        
        # Trigger key rotation immediately upon revocation per Resolved Clarifications
        if trigger_key_rotation:
            self.last_key_rotation = self.revoked_at
            # Revoked devices don't get scheduled rotations
            self.next_key_rotation = None
