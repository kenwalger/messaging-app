"""
Backend logging service for Abiqua Asset Management.

Implements structured logging per:
- Logging & Observability (#14)
- Data Classification & Retention (#8)
- Resolved Specs & Clarifications

This module handles:
- Structured JSON logging (content-free)
- Log retention and purge enforcement (90 days)
- Content validation (no sensitive data)
"""

import json
import logging
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, List, Optional
from uuid import uuid4

from src.shared.constants import LOG_RETENTION_DAYS
from src.shared.logging_types import AuditEvent, LogClassification, LogEvent, LogEventType
from src.shared.message_types import utc_now

# Configure logging per Logging & Observability (#14)
# Note: No message content logged per Data Classification (#8)
logger = logging.getLogger(__name__)


class LoggingService:
    """
    Backend logging service per Logging & Observability (#14), Section 2.
    
    Handles structured, content-free logging with retention enforcement.
    All logs are Internal classification per Data Classification (#8), Section 3.
    """
    
    def __init__(self) -> None:
        """
        Initialize logging service.
        
        Maintains in-memory log storage for demonstration.
        In production, this would write to persistent storage.
        """
        # In-memory log storage per Logging & Observability (#14)
        # Classification: Internal per Data Classification (#8), Section 3
        self._logs: List[LogEvent] = []
        self._audit_events: List[AuditEvent] = []
        self._log_lock = Lock()
    
    def log_event(
        self,
        event_type: LogEventType,
        event_data: Dict[str, Any],
        classification: LogClassification = LogClassification.INTERNAL,
    ) -> None:
        """
        Log operational event per Logging & Observability (#14), Section 3.
        
        All events are content-free per Data Classification (#8), Section 4.
        No message content, keys, or sensitive data may be logged.
        
        Args:
            event_type: Type of event (permitted types only).
            event_data: Event data dictionary (content-free).
            classification: Log classification (default Internal).
        
        Raises:
            ValueError: If event_data contains prohibited content.
        """
        # Validate event data is content-free per Logging & Observability (#14), Section 4
        self._validate_event_data(event_data)
        
        log_event = LogEvent(
            event_type=event_type,
            event_data=event_data,
            classification=classification,
        )
        
        with self._log_lock:
            self._logs.append(log_event)
        
        # Also log to standard Python logger for immediate visibility
        logger.info(f"Event logged: {event_type.value} - {json.dumps(event_data)}")
    
    def log_audit_event(
        self,
        event_type: LogEventType,
        event_data: Dict[str, Any],
        actor_id: Optional[str] = None,
    ) -> str:
        """
        Log audit event per Data Classification (#8), Section 3.
        
        Audit events are append-only and immutable.
        Retained for 90 days per Resolved TBDs.
        
        Args:
            event_type: Type of event.
            event_data: Event data dictionary (content-free).
            actor_id: Optional device ID or controller ID that triggered the event.
        
        Returns:
            Event ID (UUID string).
        
        Raises:
            ValueError: If event_data contains prohibited content.
        """
        # Validate event data is content-free
        self._validate_event_data(event_data)
        
        event_id = str(uuid4())
        audit_event = AuditEvent(
            event_id=event_id,
            event_type=event_type,
            event_data=event_data,
            actor_id=actor_id,
        )
        
        with self._log_lock:
            self._audit_events.append(audit_event)
        
        logger.info(f"Audit event logged: {event_id} - {event_type.value}")
        
        return event_id
    
    def _validate_event_data(self, event_data: Dict[str, Any]) -> None:
        """
        Validate event data is content-free per Logging & Observability (#14), Section 4.
        
        Prohibited content:
        - Message plaintext
        - Message encryption keys
        - User-generated content
        - Identity private keys
        - Any sensitive metadata beyond what's explicitly listed
        
        Args:
            event_data: Event data dictionary to validate.
        
        Raises:
            ValueError: If event_data contains prohibited content.
        """
        # Check for prohibited keys that might indicate sensitive content
        prohibited_keys = [
            "content",
            "plaintext",
            "message_content",
            "payload",
            "encrypted_payload",
            "key",
            "private_key",
            "secret",
            "password",
        ]
        
        for key in event_data.keys():
            if any(prohibited in key.lower() for prohibited in prohibited_keys):
                raise ValueError(
                    f"Event data contains prohibited key '{key}'. "
                    "No message content, keys, or sensitive data may be logged per "
                    "Logging & Observability (#14), Section 4."
                )
        
        # Check for prohibited values (large strings that might be content)
        for key, value in event_data.items():
            if isinstance(value, str) and len(value) > 1000:
                raise ValueError(
                    f"Event data value for '{key}' exceeds 1000 characters. "
                    "Large string values may indicate message content, which is prohibited."
                )
    
    def get_logs(
        self,
        event_type: Optional[LogEventType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[LogEvent]:
        """
        Get logs filtered by event type and time range.
        
        Args:
            event_type: Optional event type filter.
            start_time: Optional start time filter (inclusive).
            end_time: Optional end time filter (inclusive).
        
        Returns:
            List of log events matching the filters.
        """
        with self._log_lock:
            filtered_logs = self._logs.copy()
        
        if event_type:
            filtered_logs = [log for log in filtered_logs if log.event_type == event_type]
        
        if start_time:
            filtered_logs = [log for log in filtered_logs if log.timestamp >= start_time]
        
        if end_time:
            filtered_logs = [log for log in filtered_logs if log.timestamp <= end_time]
        
        return filtered_logs
    
    def get_audit_events(
        self,
        event_type: Optional[LogEventType] = None,
        actor_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[AuditEvent]:
        """
        Get audit events filtered by criteria.
        
        Args:
            event_type: Optional event type filter.
            actor_id: Optional actor ID filter.
            start_time: Optional start time filter (inclusive).
            end_time: Optional end time filter (inclusive).
        
        Returns:
            List of audit events matching the filters.
        """
        with self._log_lock:
            filtered_events = self._audit_events.copy()
        
        if event_type:
            filtered_events = [event for event in filtered_events if event.event_type == event_type]
        
        if actor_id:
            filtered_events = [event for event in filtered_events if event.actor_id == actor_id]
        
        if start_time:
            filtered_events = [event for event in filtered_events if event.timestamp >= start_time]
        
        if end_time:
            filtered_events = [event for event in filtered_events if event.timestamp <= end_time]
        
        return filtered_events
    
    def purge_expired_logs(self) -> int:
        """
        Purge expired logs per Data Classification (#8), Section 4.
        
        Operational logs retained for 90 days per Resolved TBDs.
        Logs older than retention period are purged automatically.
        
        Returns:
            Number of logs purged.
        """
        cutoff_time = utc_now() - timedelta(days=LOG_RETENTION_DAYS)
        
        with self._log_lock:
            initial_count = len(self._logs)
            self._logs = [log for log in self._logs if log.timestamp >= cutoff_time]
            purged_count = initial_count - len(self._logs)
            
            # Also purge audit events
            initial_audit_count = len(self._audit_events)
            self._audit_events = [
                event for event in self._audit_events if event.timestamp >= cutoff_time
            ]
            purged_audit_count = initial_audit_count - len(self._audit_events)
        
        total_purged = purged_count + purged_audit_count
        
        if total_purged > 0:
            logger.info(f"Purged {total_purged} expired logs (retention: {LOG_RETENTION_DAYS} days)")
        
        return total_purged
