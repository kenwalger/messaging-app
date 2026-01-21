"""
Controller API types and DTOs for Abiqua Asset Management.

References:
- API Contracts (#10)
- Identity Provisioning (#11)
- Copy Rules (#13)
- Resolved Specs & Clarifications

This module defines controller-facing data structures for device provisioning
and revocation operations.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.shared.message_types import utc_now


@dataclass
class ProvisionDeviceRequest:
    """
    Request DTO for device provisioning per API Contracts (#10), Section 3.1.
    
    Controller provisions a device with identity and keys.
    Creates device in Pending state per Identity Provisioning (#11), Section 3.
    """
    device_id: str  # Unique device identifier (UUID)
    public_key: str  # Public key for encryption/authentication


@dataclass
class ProvisionDeviceResponse:
    """
    Response DTO for device provisioning per API Contracts (#10), Section 3.1.
    
    Returns provisioning status and device state.
    """
    status: str  # "provisioned" per API Contracts (#10)
    device_id: str
    state: str  # "pending" per Identity Provisioning (#11), Section 3
    api_version: str = "v1"
    timestamp: datetime = None
    
    def __post_init__(self) -> None:
        """Initialize timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = utc_now()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.status,
            "device_id": self.device_id,
            "state": self.state,
            "api_version": self.api_version,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ConfirmProvisioningRequest:
    """
    Request DTO for confirming device provisioning per Identity Provisioning (#11), Section 3.
    
    Device confirms receipt of provisioning data.
    Transitions: Pending → Provisioned per State Machines (#7), Section 5.
    """
    device_id: str  # Device identifier to confirm


@dataclass
class ConfirmProvisioningResponse:
    """
    Response DTO for confirming device provisioning.
    
    Returns confirmation status and device state.
    """
    status: str  # "confirmed" or "error"
    device_id: str
    state: Optional[str] = None  # "provisioned" if successful
    api_version: str = "v1"
    timestamp: datetime = None
    
    def __post_init__(self) -> None:
        """Initialize timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = utc_now()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "status": self.status,
            "device_id": self.device_id,
            "api_version": self.api_version,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.state:
            result["state"] = self.state
        return result


@dataclass
class RevokeDeviceRequest:
    """
    Request DTO for device revocation per API Contracts (#10), Section 3.2.
    
    Controller revokes device; triggers secure deletion on device.
    Revocation is immediate and irreversible per Identity Provisioning (#11), Section 5.
    """
    device_id: str  # Device identifier to revoke


@dataclass
class RevokeDeviceResponse:
    """
    Response DTO for device revocation per API Contracts (#10), Section 3.2.
    
    Returns revocation status.
    """
    status: str  # "revoked" per API Contracts (#10)
    device_id: str
    affected_conversations: int  # Number of conversations affected
    conversations_closed: int  # Number of conversations closed
    api_version: str = "v1"
    timestamp: datetime = None
    
    def __post_init__(self) -> None:
        """Initialize timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = utc_now()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.status,
            "device_id": self.device_id,
            "affected_conversations": self.affected_conversations,
            "conversations_closed": self.conversations_closed,
            "api_version": self.api_version,
            "timestamp": self.timestamp.isoformat(),
        }
