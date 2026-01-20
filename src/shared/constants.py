"""
Shared constants for Abiqua Asset Management.

References:
- Resolved Specs & Clarifications
- Functional Specification (#6)
- API Contracts (#10)
"""

# Message delivery constants
MAX_GROUP_SIZE = 50
DEFAULT_MESSAGE_EXPIRATION_DAYS = 7
MAX_OFFLINE_MESSAGES = 500
MAX_OFFLINE_STORAGE_MB = 50
MAX_MESSAGE_PAYLOAD_SIZE_KB = 50
MAX_DELIVERY_RETRIES = 5

# Network constants
REST_POLLING_INTERVAL_SECONDS = 30
WEBSOCKET_RECONNECT_TIMEOUT_SECONDS = 15
CLOCK_SKEW_TOLERANCE_MINUTES = 2

# API endpoints per API Contracts (#10)
API_ENDPOINT_SEND_MESSAGE = "/api/message/send"
API_ENDPOINT_RECEIVE_MESSAGE = "/api/message/receive"
API_ENDPOINT_LOG_EVENT = "/api/log/event"

# HTTP headers per API Contracts (#10), Section 5
HEADER_DEVICE_ID = "X-Device-ID"
HEADER_CONTROLLER_KEY = "X-Controller-Key"

# Error messages per Copy Rules (#13), Section 4
ERROR_NETWORK_UNAVAILABLE = "Unable to send messages; retry will occur automatically"
ERROR_BACKEND_UNREACHABLE = "Unable to connect; retry will occur automatically"
ERROR_EMPTY_MESSAGE = "Cannot send empty message"
ERROR_MESSAGING_DISABLED = "Messaging Disabled"

# Log event types per Logging & Observability (#14), Section 3
LOG_EVENT_MESSAGE_ATTEMPTED = "message_attempted"
LOG_EVENT_DELIVERY_FAILED = "delivery_failed"
LOG_EVENT_POLICY_ENFORCED = "policy_enforced"
