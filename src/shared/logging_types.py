"""
Logging types and event models for Abiqua Asset Management.

References:
- Logging & Observability (#14)
- Data Classification & Retention (#8)
- Resolved Specs & Clarifications
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from src.shared.message_types import utc_now


class LogEventType(Enum):
    """
    Permitted log event types per Logging & Observability (#14), Section 3.
    
    All events are content-free per Data Classification (#8), Section 3.
    """
    DEVICE_PROVISIONED = "device_provisioned"
    DEVICE_REVOKED = "device_revoked"
    MESSAGE_ATTEMPTED = "message_attempted"
    POLICY_ENFORCED = "policy_enforced"
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    DELIVERY_FAILED = "delivery_failed"


class LogClassification(Enum):
    """
    Log classification levels per Data Classification (#8), Section 2.
    
    All operational logs are Internal classification per Logging & Observability (#14).
    """
    INTERNAL = "internal"
    RESTRICTED = "restricted"  # For metadata-only logs (e.g., message_attempted, delivery_failed)


@dataclass
class LogEvent:
    """
    Structured log event per Logging & Observability (#14), Section 2.
    
    All log events are:
    - Content-free (no plaintext messages or cryptographic material)
    - Deterministic (only defined events)
    - Traceable (maps to state machine or system action)
    - Time-stamped (UTC timestamp)
    
    Classification: Internal per Data Classification (#8), Section 3.
    """
    event_type: LogEventType
    timestamp: datetime = field(default_factory=utc_now)
    event_data: Dict[str, Any] = field(default_factory=dict)
    classification: LogClassification = LogClassification.INTERNAL
    
    def to_json(self) -> str:
        """
        Serialize log event to JSON per Logging & Observability (#14), Section 2.
        
        Returns:
            JSON string representation of the log event.
        """
        return json.dumps(
            {
                "event_type": self.event_type.value,
                "timestamp": self.timestamp.isoformat(),
                "event_data": self.event_data,
                "classification": self.classification.value,
            },
            sort_keys=True,
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "LogEvent":
        """
        Deserialize log event from JSON.
        
        Args:
            json_str: JSON string representation of the log event.
        
        Returns:
            LogEvent object.
        """
        data = json.loads(json_str)
        return cls(
            event_type=LogEventType(data["event_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            event_data=data["event_data"],
            classification=LogClassification(data["classification"]),
        )


@dataclass
class AuditEvent:
    """
    Audit event model per Data Classification (#8), Section 3.
    
    Audit events are:
    - Append-only (immutable)
    - Content-free (no message content or keys)
    - Retained per organizational policy (90 days per Resolved TBDs)
    
    Classification: Internal per Data Classification (#8), Section 3.
    """
    event_id: str  # Unique event identifier
    event_type: LogEventType
    timestamp: datetime = field(default_factory=utc_now)
    event_data: Dict[str, Any] = field(default_factory=dict)
    actor_id: Optional[str] = None  # Device ID or controller ID that triggered the event
    
    def to_json(self) -> str:
        """
        Serialize audit event to JSON.
        
        Returns:
            JSON string representation of the audit event.
        """
        return json.dumps(
            {
                "event_id": self.event_id,
                "event_type": self.event_type.value,
                "timestamp": self.timestamp.isoformat(),
                "event_data": self.event_data,
                "actor_id": self.actor_id,
            },
            sort_keys=True,
        )
