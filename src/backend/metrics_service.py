"""
Backend metrics service for Abiqua Asset Management.

Implements metrics collection and aggregation per:
- Logging & Observability (#14), Section 5
- Resolved Specs & Clarifications

This module handles:
- Metrics aggregation in 1-hour windows
- Alert threshold logic (≥5 failed deliveries in 1-hour window)
- Content-free metrics (no sensitive data)
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Dict, List, Optional

from src.shared.message_types import utc_now

from src.shared.constants import (
    ALERT_THRESHOLD_FAILED_DELIVERIES,
    METRICS_AGGREGATION_WINDOW_HOURS,
)

# Configure logging per Logging & Observability (#14)
logger = logging.getLogger(__name__)


class MetricsService:
    """
    Backend metrics service per Logging & Observability (#14), Section 5.
    
    Collects and aggregates metrics in 1-hour windows per Resolved TBDs.
    Metrics are content-free (no sensitive data) per Logging & Observability (#14), Section 5.
    """
    
    def __init__(self) -> None:
        """
        Initialize metrics service.
        
        Maintains metrics aggregated in 1-hour windows.
        """
        # Metrics storage: window_start_time -> metric_name -> value
        # Classification: Internal per Data Classification (#8), Section 3
        self._metrics: Dict[datetime, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._metrics_lock = Lock()
        
        # Alert state tracking
        self._alerts_triggered: List[Dict[str, any]] = []
    
    def record_metric(
        self,
        metric_name: str,
        value: int = 1,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Record a metric value per Logging & Observability (#14), Section 5.
        
        Metrics are aggregated in 1-hour windows per Resolved TBDs.
        Metrics must not include sensitive content per Logging & Observability (#14), Section 5.
        
        Args:
            metric_name: Name of the metric (e.g., "active_devices", "messages_queued").
            value: Metric value (default 1 for counting).
            timestamp: Optional timestamp (defaults to current time).
        """
        if timestamp is None:
            timestamp = utc_now()
        
        # Round down to nearest hour for aggregation window
        window_start = timestamp.replace(minute=0, second=0, microsecond=0)
        
        with self._metrics_lock:
            self._metrics[window_start][metric_name] += value
        
        logger.debug(f"Metric recorded: {metric_name}={value} (window: {window_start.isoformat()})")
    
    def get_metric(
        self,
        metric_name: str,
        window_start: Optional[datetime] = None,
    ) -> int:
        """
        Get aggregated metric value for a time window.
        
        Args:
            metric_name: Name of the metric.
            window_start: Optional window start time (defaults to current hour).
        
        Returns:
            Aggregated metric value for the window.
        """
        if window_start is None:
            window_start = utc_now().replace(minute=0, second=0, microsecond=0)
        else:
            window_start = window_start.replace(minute=0, second=0, microsecond=0)
        
        with self._metrics_lock:
            return self._metrics.get(window_start, {}).get(metric_name, 0)
    
    def get_metrics_for_window(
        self,
        window_start: datetime,
    ) -> Dict[str, int]:
        """
        Get all metrics for a specific time window.
        
        Args:
            window_start: Window start time (rounded to hour).
        
        Returns:
            Dictionary of metric_name -> value for the window.
        """
        window_start = window_start.replace(minute=0, second=0, microsecond=0)
        
        with self._metrics_lock:
            return dict(self._metrics.get(window_start, {}))
    
    def check_alert_thresholds(self) -> List[Dict[str, Any]]:
        """
        Check alert thresholds per Resolved TBDs.
        
        Alert triggered if ≥5 failed deliveries in a 1-hour window per Resolved TBDs.
        
        Returns:
            List of triggered alerts (each alert is a dictionary with alert details).
        """
        current_window = utc_now().replace(minute=0, second=0, microsecond=0)
        
        with self._metrics_lock:
            failed_deliveries = self._metrics.get(current_window, {}).get("failed_deliveries", 0)
        
        triggered_alerts: List[Dict[str, Any]] = []
        
        # Check failed deliveries threshold per Resolved TBDs
        if failed_deliveries >= ALERT_THRESHOLD_FAILED_DELIVERIES:
            alert = {
                "alert_type": "failed_deliveries_threshold",
                "threshold": ALERT_THRESHOLD_FAILED_DELIVERIES,
                "actual_value": failed_deliveries,
                "window_start": current_window.isoformat(),
                "timestamp": utc_now().isoformat(),
                "message": f"Failed delivery count ({failed_deliveries}) exceeds threshold "
                          f"({ALERT_THRESHOLD_FAILED_DELIVERIES}) in 1-hour window",
            }
            triggered_alerts.append(alert)
            self._alerts_triggered.append(alert)
            logger.warning(
                f"Alert triggered: {alert['message']} per Logging & Observability (#14), Section 6"
            )
        
        return triggered_alerts
    
    def get_active_devices_count(self, window_start: Optional[datetime] = None) -> int:
        """
        Get count of active devices per Logging & Observability (#14), Section 5.
        
        Args:
            window_start: Optional window start time (defaults to current hour).
        
        Returns:
            Count of active devices.
        """
        return self.get_metric("active_devices", window_start)
    
    def get_messages_queued_count(self, window_start: Optional[datetime] = None) -> int:
        """
        Get count of messages queued per Logging & Observability (#14), Section 5.
        
        Args:
            window_start: Optional window start time (defaults to current hour).
        
        Returns:
            Count of messages queued.
        """
        return self.get_metric("messages_queued", window_start)
    
    def get_failed_deliveries_count(self, window_start: Optional[datetime] = None) -> int:
        """
        Get count of failed deliveries per Logging & Observability (#14), Section 5.
        
        Args:
            window_start: Optional window start time (defaults to current hour).
        
        Returns:
            Count of failed deliveries.
        """
        return self.get_metric("failed_deliveries", window_start)
    
    def get_revoked_devices_count(self, window_start: Optional[datetime] = None) -> int:
        """
        Get count of revoked devices per Logging & Observability (#14), Section 5.
        
        Args:
            window_start: Optional window start time (defaults to current hour).
        
        Returns:
            Count of revoked devices.
        """
        return self.get_metric("revoked_devices", window_start)
    
    def record_failed_delivery(
        self,
        message_id: str,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Record a failed delivery event.
        
        This increments the failed_deliveries metric and checks alert thresholds.
        
        Args:
            message_id: Message ID that failed delivery (for logging only, not stored in metric).
            timestamp: Optional timestamp (defaults to current time).
        """
        self.record_metric("failed_deliveries", value=1, timestamp=timestamp)
        
        # Check alert thresholds after recording
        self.check_alert_thresholds()
    
    def purge_old_metrics(self, retention_hours: int = 24) -> int:
        """
        Purge metrics older than retention period.
        
        Args:
            retention_hours: Number of hours to retain metrics (default 24 hours).
        
        Returns:
            Number of metric windows purged.
        """
        cutoff_time = utc_now() - timedelta(hours=retention_hours)
        cutoff_window = cutoff_time.replace(minute=0, second=0, microsecond=0)
        
        with self._metrics_lock:
            initial_count = len(self._metrics)
            self._metrics = {
                window: metrics
                for window, metrics in self._metrics.items()
                if window >= cutoff_window
            }
            purged_count = initial_count - len(self._metrics)
        
        if purged_count > 0:
            logger.debug(f"Purged {purged_count} old metric windows")
        
        return purged_count
