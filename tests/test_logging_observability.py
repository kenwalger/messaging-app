"""
Unit tests for logging, observability, and audit enforcement.

References:
- Logging & Observability (#14)
- Data Classification & Retention (#8)
- Resolved Specs & Clarifications
"""

import unittest
from datetime import datetime, timedelta
from uuid import uuid4

from src.backend.logging_service import LoggingService
from src.backend.metrics_service import MetricsService
from src.shared.constants import (
    ALERT_THRESHOLD_FAILED_DELIVERIES,
    LOG_RETENTION_DAYS,
    METRICS_AGGREGATION_WINDOW_HOURS,
)
from src.shared.logging_types import LogClassification, LogEvent, LogEventType
from src.shared.message_types import utc_now


class TestLoggingService(unittest.TestCase):
    """Test cases for LoggingService per Logging & Observability (#14)."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.service = LoggingService()
    
    def test_log_event_content_free(self) -> None:
        """
        Test log event creation per Logging & Observability (#14), Section 2.
        
        All events are content-free per Data Classification (#8), Section 4.
        """
        event_data = {
            "device_id": "device-001",
            "timestamp": utc_now().isoformat(),
        }
        
        self.service.log_event(
            event_type=LogEventType.DEVICE_PROVISIONED,
            event_data=event_data,
        )
        
        logs = self.service.get_logs()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].event_type, LogEventType.DEVICE_PROVISIONED)
        self.assertEqual(logs[0].event_data, event_data)
    
    def test_log_event_prohibited_content(self) -> None:
        """
        Test log event validation per Logging & Observability (#14), Section 4.
        
        Prohibited content includes message plaintext, keys, and sensitive data.
        """
        # Test prohibited key: "content"
        with self.assertRaises(ValueError) as context:
            self.service.log_event(
                event_type=LogEventType.MESSAGE_ATTEMPTED,
                event_data={"message_content": "test"},
            )
        self.assertIn("prohibited", str(context.exception).lower())
        
        # Test prohibited key: "key"
        with self.assertRaises(ValueError) as context:
            self.service.log_event(
                event_type=LogEventType.DEVICE_PROVISIONED,
                event_data={"private_key": "test-key"},
            )
        self.assertIn("prohibited", str(context.exception).lower())
        
        # Test large string value (potential content)
        with self.assertRaises(ValueError) as context:
            self.service.log_event(
                event_type=LogEventType.MESSAGE_ATTEMPTED,
                event_data={"data": "x" * 1001},
            )
        self.assertIn("exceeds", str(context.exception).lower())
    
    def test_log_event_permitted_fields(self) -> None:
        """
        Test permitted log event fields per Logging & Observability (#14), Section 3.
        
        Permitted fields: message_id, sender_id, recipient_count, device_id, etc.
        """
        # Test message_attempted event with permitted fields
        self.service.log_event(
            event_type=LogEventType.MESSAGE_ATTEMPTED,
            event_data={
                "message_id": str(uuid4()),
                "sender_id": "device-001",
                "recipient_count": 2,
                "timestamp": utc_now().isoformat(),
            },
        )
        
        logs = self.service.get_logs(event_type=LogEventType.MESSAGE_ATTEMPTED)
        self.assertEqual(len(logs), 1)
        self.assertIn("message_id", logs[0].event_data)
        self.assertIn("sender_id", logs[0].event_data)
        self.assertIn("recipient_count", logs[0].event_data)
    
    def test_log_audit_event(self) -> None:
        """
        Test audit event logging per Data Classification (#8), Section 3.
        
        Audit events are append-only and immutable.
        """
        event_id = self.service.log_audit_event(
            event_type=LogEventType.DEVICE_REVOKED,
            event_data={"device_id": "device-001"},
            actor_id="controller-001",
        )
        
        self.assertIsNotNone(event_id)
        
        audit_events = self.service.get_audit_events()
        self.assertEqual(len(audit_events), 1)
        self.assertEqual(audit_events[0].event_id, event_id)
        self.assertEqual(audit_events[0].actor_id, "controller-001")
    
    def test_log_retention_purge(self) -> None:
        """
        Test log retention and purge per Data Classification (#8), Section 4.
        
        Operational logs retained for 90 days per Resolved TBDs.
        """
        # Create old log (beyond retention period)
        old_timestamp = utc_now() - timedelta(days=LOG_RETENTION_DAYS + 1)
        
        # Manually add old log (bypassing timestamp generation)
        old_event = LogEvent(
            event_type=LogEventType.SYSTEM_START,
            timestamp=old_timestamp,
            event_data={},
        )
        self.service._logs.append(old_event)
        
        # Create recent log
        self.service.log_event(
            event_type=LogEventType.SYSTEM_START,
            event_data={},
        )
        
        # Purge expired logs
        purged_count = self.service.purge_expired_logs()
        
        # Verify old log purged, recent log retained
        self.assertGreater(purged_count, 0)
        logs = self.service.get_logs()
        self.assertEqual(len(logs), 1)  # Only recent log remains
        self.assertGreater(logs[0].timestamp, old_timestamp)


class TestMetricsService(unittest.TestCase):
    """Test cases for MetricsService per Logging & Observability (#14), Section 5."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.service = MetricsService()
    
    def test_record_metric(self) -> None:
        """
        Test metric recording per Logging & Observability (#14), Section 5.
        
        Metrics are aggregated in 1-hour windows per Resolved TBDs.
        """
        self.service.record_metric("active_devices", value=5)
        self.service.record_metric("active_devices", value=3)
        
        count = self.service.get_active_devices_count()
        self.assertEqual(count, 8)  # Aggregated value
    
    def test_metrics_aggregation_window(self) -> None:
        """
        Test metrics aggregation in 1-hour windows per Resolved TBDs.
        
        Metrics are aggregated per hour window.
        """
        current_time = utc_now()
        window_start = current_time.replace(minute=0, second=0, microsecond=0)
        
        # Record metrics in same window
        self.service.record_metric("messages_queued", value=10, timestamp=current_time)
        self.service.record_metric("messages_queued", value=5, timestamp=current_time)
        
        # Record metric in different window (previous hour)
        previous_window = window_start - timedelta(hours=1)
        self.service.record_metric("messages_queued", value=20, timestamp=previous_window)
        
        # Verify aggregation per window
        current_count = self.service.get_messages_queued_count(window_start)
        previous_count = self.service.get_messages_queued_count(previous_window)
        
        self.assertEqual(current_count, 15)  # 10 + 5
        self.assertEqual(previous_count, 20)  # Separate window
    
    def test_alert_threshold_failed_deliveries(self) -> None:
        """
        Test alert threshold logic per Resolved TBDs.
        
        Alert triggered if ≥5 failed deliveries in a 1-hour window.
        """
        # Record 4 failed deliveries (below threshold)
        for _ in range(4):
            self.service.record_failed_delivery(str(uuid4()))
        
        alerts = self.service.check_alert_thresholds()
        self.assertEqual(len(alerts), 0)  # No alert yet
        
        # Record 1 more failed delivery (reaches threshold)
        self.service.record_failed_delivery(str(uuid4()))
        
        alerts = self.service.check_alert_thresholds()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["alert_type"], "failed_deliveries_threshold")
        self.assertEqual(alerts[0]["actual_value"], 5)
        self.assertEqual(alerts[0]["threshold"], ALERT_THRESHOLD_FAILED_DELIVERIES)
    
    def test_metrics_content_free(self) -> None:
        """
        Test metrics are content-free per Logging & Observability (#14), Section 5.
        
        Metrics must not include sensitive content.
        """
        # Metrics only store counts, not content
        self.service.record_metric("failed_deliveries", value=1)
        self.service.record_metric("messages_queued", value=5)
        
        # Verify metrics are numeric counts only
        metrics = self.service.get_metrics_for_window(utc_now().replace(minute=0, second=0, microsecond=0))
        self.assertIn("failed_deliveries", metrics)
        self.assertIn("messages_queued", metrics)
        self.assertIsInstance(metrics["failed_deliveries"], int)
        self.assertIsInstance(metrics["messages_queued"], int)
    
    def test_purge_old_metrics(self) -> None:
        """
        Test purging old metrics.
        
        Old metric windows are purged to manage storage.
        """
        current_time = utc_now()
        current_window = current_time.replace(minute=0, second=0, microsecond=0)
        old_window = current_window - timedelta(hours=25)
        
        # Record metrics in current and old windows
        self.service.record_metric("active_devices", value=5, timestamp=current_time)
        self.service.record_metric("active_devices", value=3, timestamp=old_window)
        
        # Purge metrics older than 24 hours
        purged_count = self.service.purge_old_metrics(retention_hours=24)
        
        # Verify old metrics purged
        self.assertGreater(purged_count, 0)
        current_count = self.service.get_active_devices_count(current_window)
        old_count = self.service.get_active_devices_count(old_window)
        
        self.assertEqual(current_count, 5)  # Current window retained
        self.assertEqual(old_count, 0)  # Old window purged


class TestLogEventTypes(unittest.TestCase):
    """Test cases for log event types per Logging & Observability (#14), Section 3."""
    
    def test_permitted_event_types(self) -> None:
        """
        Test all permitted event types per Logging & Observability (#14), Section 3.
        
        Permitted types: device_provisioned, device_revoked, message_attempted,
        policy_enforced, system_start, system_stop, delivery_failed.
        """
        permitted_types = [
            LogEventType.DEVICE_PROVISIONED,
            LogEventType.DEVICE_REVOKED,
            LogEventType.MESSAGE_ATTEMPTED,
            LogEventType.POLICY_ENFORCED,
            LogEventType.SYSTEM_START,
            LogEventType.SYSTEM_STOP,
            LogEventType.DELIVERY_FAILED,
        ]
        
        service = LoggingService()
        
        for event_type in permitted_types:
            service.log_event(
                event_type=event_type,
                event_data={"test": "data"},
            )
        
        logs = service.get_logs()
        self.assertEqual(len(logs), len(permitted_types))
    
    def test_log_event_json_serialization(self) -> None:
        """
        Test log event JSON serialization per Logging & Observability (#14), Section 2.
        
        Logs are structured JSON format.
        """
        event = LogEvent(
            event_type=LogEventType.MESSAGE_ATTEMPTED,
            event_data={"message_id": "test-id", "sender_id": "device-001"},
        )
        
        json_str = event.to_json()
        self.assertIsInstance(json_str, str)
        
        # Verify can deserialize
        deserialized = LogEvent.from_json(json_str)
        self.assertEqual(deserialized.event_type, event.event_type)
        self.assertEqual(deserialized.event_data, event.event_data)


if __name__ == "__main__":
    unittest.main()
