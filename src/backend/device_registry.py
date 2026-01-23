"""
Backend device registry service for Abiqua Asset Management.

Implements device identity tracking and enforcement per:
- Identity Provisioning (#11)
- State Machines (#7), Section 5
- Functional Specification (#6), Section 3.1
- Data Classification & Retention (#8)
- Resolved Specs & Clarifications

This module handles:
- Device identity state tracking (Restricted classification)
- Identity enforcement (server-side only)
- Revocation handling
- Key rotation scheduling and triggers
"""

import logging
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, List, Optional, Set

from src.shared.constants import MAX_GROUP_SIZE
from src.shared.device_identity_types import DeviceIdentity, DeviceIdentityState
from src.shared.message_types import utc_now

# Configure logging per Logging & Observability (#14)
# Note: No device keys or sensitive data logged per Data Classification (#8)
logger = logging.getLogger(__name__)


class DeviceRegistry:
    """
    Backend device registry service per Identity Provisioning (#11), Section 2.
    
    Tracks device identity states (Restricted classification per Data Classification #8, Section 3).
    Enforces identity-based permissions server-side per Functional Spec (#6), Section 3.2.
    """
    
    def __init__(self, demo_mode: bool = False) -> None:
        """
        Initialize device registry.
        
        Maintains device identity state tracking in memory.
        Classification: Restricted per Data Classification (#8), Section 3.
        
        Args:
            demo_mode: If True, enables demo mode with lenient device validation and activity TTL.
        """
        # Device identity storage per Identity Provisioning (#11), Section 2
        # Classification: Restricted per Data Classification (#8), Section 3
        self._devices: Dict[str, DeviceIdentity] = {}
        self._device_lock = Lock()
        
        # Demo mode: Track device activity with TTL (5 minutes)
        # Devices are considered "active" if seen within TTL window
        self._demo_mode = demo_mode
        self._device_last_seen: Dict[str, datetime] = {}  # device_id -> last_seen timestamp
        self._demo_activity_ttl = timedelta(minutes=5)  # 5 minute TTL for demo mode
    
    def is_demo_mode(self) -> bool:
        """
        Check if demo mode is enabled.
        
        Returns:
            True if demo mode is enabled, False otherwise.
        """
        return self._demo_mode
    
    def register_device(
        self,
        device_id: str,
        public_key: str,
        controller_id: Optional[str] = None,
    ) -> DeviceIdentity:
        """
        Register a new device identity per Identity Provisioning (#11), Section 3.
        
        Creates device in Pending state per State Machines (#7), Section 5.
        Only Controllers can initiate provisioning per State Machines (#7).
        
        Args:
            device_id: Unique device identifier (UUID).
            public_key: Public key for encryption/authentication.
            controller_id: Optional controller identifier that provisioned this device.
        
        Returns:
            DeviceIdentity object in Pending state.
        
        Raises:
            ValueError: If device_id already exists.
        """
        with self._device_lock:
            if device_id in self._devices:
                raise ValueError(f"Device {device_id} already registered")
            
            device = DeviceIdentity(
                device_id=device_id,
                state=DeviceIdentityState.PENDING,
                public_key=public_key,
                controller_id=controller_id,
            )
            
            self._devices[device_id] = device
        
        logger.info(f"Registered device {device_id} in Pending state")
        
        return device
    
    def provision_device(self, device_id: str) -> bool:
        """
        Provision device per Identity Provisioning (#11), Section 3.
        
        Transitions: Pending → Provisioned per State Machines (#7), Section 5.
        Trigger: Device receives provisioning data and stores keys in secure keystore per Lifecycle Playbooks (#15), Section 2.
        
        Args:
            device_id: Device identifier to provision.
        
        Returns:
            True if device provisioned, False if device not found or invalid state.
        """
        with self._device_lock:
            if device_id not in self._devices:
                logger.warning(f"Device {device_id} not found for provisioning")
                return False
            
            device = self._devices[device_id]
            
            try:
                device.transition_to_provisioned()
            except ValueError as e:
                logger.warning(f"Cannot provision device {device_id}: {e}")
                return False
        
        logger.info(f"Device {device_id} provisioned, now in Provisioned state")
        
        return True
    
    def confirm_provisioning(self, device_id: str) -> bool:
        """
        Confirm device provisioning per Identity Provisioning (#11), Section 3.
        
        Transitions: Provisioned → Active per State Machines (#7), Section 5.
        Trigger: Device confirms receipt via /api/device/provision/confirm per Lifecycle Playbooks (#15), Section 2.
        
        Args:
            device_id: Device identifier to confirm.
        
        Returns:
            True if provisioning confirmed and device activated, False if device not found or invalid state.
        """
        with self._device_lock:
            if device_id not in self._devices:
                logger.warning(f"Device {device_id} not found for provisioning confirmation")
                return False
            
            device = self._devices[device_id]
            
            try:
                device.transition_to_active()
            except ValueError as e:
                logger.warning(f"Cannot confirm provisioning for device {device_id}: {e}")
                return False
        
        logger.info(f"Device {device_id} confirmed provisioning, now Active")
        
        return True
    
    def revoke_device(
        self,
        device_id: str,
        controller_id: Optional[str] = None,
    ) -> bool:
        """
        Revoke device per Identity Provisioning (#11), Section 5 and Lifecycle Playbooks (#15), Section 3.
        
        Transitions: Active → Revoked per State Machines (#7), Section 5.
        Trigger: Controller sends /api/device/revoke per Lifecycle Playbooks (#15), Section 3.
        
        Revocation is immediate and irreversible per Identity Provisioning (#11), Section 5.
        Triggers key rotation immediately upon revocation per Resolved Clarifications.
        
        Args:
            device_id: Device identifier to revoke.
            controller_id: Optional controller identifier that revoked this device.
        
        Returns:
            True if device revoked, False if device not found or already revoked.
        """
        with self._device_lock:
            if device_id not in self._devices:
                logger.warning(f"Device {device_id} not found for revocation")
                return False
            
            device = self._devices[device_id]
            
            if device.is_revoked():
                logger.debug(f"Device {device_id} already revoked")
                return False
            
            try:
                device.transition_to_revoked(trigger_key_rotation=True)
            except ValueError as e:
                logger.warning(f"Cannot revoke device {device_id}: {e}")
                return False
        
        logger.warning(f"Device {device_id} revoked by controller {controller_id or 'unknown'}")
        
        return True
    
    def is_device_active(self, device_id: str) -> bool:
        """
        Check if device is active (provisioned and not revoked) per Identity Provisioning (#11).
        
        Used for permission enforcement across the system.
        Only Active devices can send messages, create/join conversations per Functional Spec (#6).
        
        In demo mode: Devices are considered active if seen within TTL window (5 minutes),
        even if not in Active state. This allows HTTP-first messaging without WebSocket dependency.
        
        Args:
            device_id: Device identifier to check.
        
        Returns:
            True if device exists and is in Active state, False otherwise.
            In demo mode: Also returns True if device was seen within TTL window.
        """
        with self._device_lock:
            device = self._devices.get(device_id)
            
            # Demo mode: Check activity TTL
            if self._demo_mode:
                last_seen = self._device_last_seen.get(device_id)
                if last_seen:
                    time_since_seen = utc_now() - last_seen
                    if time_since_seen <= self._demo_activity_ttl:
                        # Device seen within TTL window - consider active for demo purposes
                        return True
            
            if device is None:
                return False
            
            return device.is_active()
    
    def mark_device_seen(self, device_id: str) -> None:
        """
        Mark device as seen (for demo mode activity tracking).
        
        In demo mode, this updates the last_seen timestamp to keep device "active"
        within the TTL window, allowing HTTP-first messaging without WebSocket dependency.
        
        Args:
            device_id: Device identifier to mark as seen.
        """
        if self._demo_mode:
            with self._device_lock:
                self._device_last_seen[device_id] = utc_now()
    
    def get_device_identity(self, device_id: str) -> Optional[DeviceIdentity]:
        """
        Get device identity information.
        
        Args:
            device_id: Device identifier.
        
        Returns:
            DeviceIdentity object if device exists, None otherwise.
        """
        with self._device_lock:
            return self._devices.get(device_id)
    
    def can_send_messages(self, device_id: str) -> bool:
        """
        Check if device can send messages per Functional Spec (#6), Section 4.2.
        
        Server-side enforcement: Only Active devices can send messages.
        Revoked devices cannot send messages per Resolved Clarifications (#38).
        
        Args:
            device_id: Device identifier to check.
        
        Returns:
            True if device can send messages, False otherwise.
        """
        with self._device_lock:
            device = self._devices.get(device_id)
            if device is None:
                return False
            
            return device.can_send_messages()
    
    def can_create_conversations(self, device_id: str) -> bool:
        """
        Check if device can create conversations per Functional Spec (#6), Section 4.1.
        
        Server-side enforcement: Only Active devices can create conversations.
        Revoked devices cannot create conversations per Resolved Clarifications (#38).
        
        Args:
            device_id: Device identifier to check.
        
        Returns:
            True if device can create conversations, False otherwise.
        """
        with self._device_lock:
            device = self._devices.get(device_id)
            if device is None:
                return False
            
            return device.can_create_conversations()
    
    def can_join_conversations(self, device_id: str) -> bool:
        """
        Check if device can join conversations per State Machines (#7), Section 4.
        
        Server-side enforcement: Only Active devices can join conversations.
        Revoked devices cannot join conversations per Resolved Clarifications (#38).
        
        Args:
            device_id: Device identifier to check.
        
        Returns:
            True if device can join conversations, False otherwise.
        """
        with self._device_lock:
            device = self._devices.get(device_id)
            if device is None:
                return False
            
            return device.can_join_conversations()
    
    def can_read_conversations(self, device_id: str) -> bool:
        """
        Check if device can read historical conversations per Resolved Clarifications (#38).
        
        Active devices can read conversations.
        Revoked devices can read historical conversations (neutral enterprise mode).
        
        Args:
            device_id: Device identifier to check.
        
        Returns:
            True if device can read conversations, False otherwise.
        """
        with self._device_lock:
            device = self._devices.get(device_id)
            if device is None:
                return False
            
            return device.can_read_conversations()
    
    def get_devices_needing_key_rotation(self) -> List[str]:
        """
        Get list of device IDs that need key rotation per Resolved TBDs.
        
        Key rotation required:
        - Every 90 days (scheduled rotation)
        - Immediately upon revocation (handled in transition_to_revoked)
        
        Returns:
            List of device IDs that need key rotation.
        """
        with self._device_lock:
            devices_needing_rotation: List[str] = []
            
            for device_id, device in self._devices.items():
                if device.needs_key_rotation():
                    devices_needing_rotation.append(device_id)
            
            return devices_needing_rotation
    
    def rotate_device_key(
        self,
        device_id: str,
        new_public_key: str,
    ) -> bool:
        """
        Rotate device key per Resolved TBDs.
        
        Key rotation occurs:
        - Every 90 days (scheduled rotation)
        - Immediately upon revocation (handled in transition_to_revoked)
        
        Args:
            device_id: Device identifier.
            new_public_key: New public key for the device.
        
        Returns:
            True if key rotated, False if device not found or invalid state.
        """
        with self._device_lock:
            if device_id not in self._devices:
                logger.warning(f"Device {device_id} not found for key rotation")
                return False
            
            device = self._devices[device_id]
            
            # Update public key
            device.public_key = new_public_key
            device.last_key_rotation = utc_now()
            
            # Schedule next rotation (90 days) unless revoked
            if not device.is_revoked():
                device.next_key_rotation = utc_now() + timedelta(days=90)
            else:
                # Revoked devices don't get scheduled rotations
                device.next_key_rotation = None
        
        logger.info(f"Key rotated for device {device_id}")
        
        return True
    
    def get_all_active_devices(self) -> List[str]:
        """
        Get list of all active device IDs.
        
        Returns:
            List of device IDs in Active state.
        """
        with self._device_lock:
            return [
                device_id
                for device_id, device in self._devices.items()
                if device.is_active()
            ]
    
    def get_all_revoked_devices(self) -> List[str]:
        """
        Get list of all revoked device IDs.
        
        Returns:
            List of device IDs in Revoked state.
        """
        with self._device_lock:
            return [
                device_id
                for device_id, device in self._devices.items()
                if device.is_revoked()
            ]
