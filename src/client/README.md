# Message Delivery Module

**Module:** `src/client/message-delivery.py`

## Overview

Client-side message delivery module implementing the complete message lifecycle per:
- Functional Specification (#6), Sections 4.2-4.5, 10
- State Machines (#7), Section 3
- Data Classification & Retention (#8)
- Lifecycle Playbooks (#15), Section 5
- Resolved Specs & Clarifications

## Features

### Message Creation
- Encrypts message content on device before transmission
- Generates UUID v4 message IDs (client-side)
- Assigns metadata: sender_id, recipients, timestamps, expiration
- Validates constraints: max group size (50), max payload (50KB)

### Message Delivery
- **WebSocket delivery** (preferred): Real-time delivery with ACK per message ID
- **REST fallback**: Polling every 30 seconds when WebSocket unavailable
- Automatic reconnect with exponential backoff
- Falls back to REST polling if reconnect fails >15s

### Offline Queuing
- Queues encrypted messages when network unavailable
- Enforces storage limits: max 500 messages or 50MB
- Eviction only for expired messages (oldest first)
- Processes queue on network reconnection

### Message Expiration
- Device-local expiration timers (default 7 days)
- Immediate deletion on expiration
- No grace period per Resolved Clarifications
- Expired messages removed from queue immediately

### Duplicate Detection
- Primary: Message ID comparison
- Secondary: Content hash comparison
- Silently discards duplicates

### Retry Logic
- Maximum 5 retry attempts
- Retries only within expiration window
- Marks as Failed after max retries

## State Transitions

Per State Machines (#7), Section 3:

```
Created → PendingDelivery → Delivered/Failed → Active → Expired
```

## Usage Example

```python
from src.client.message_delivery import MessageDeliveryService

# Initialize service
service = MessageDeliveryService(
    device_id="device-001",
    encryption_service=encryption_service,
    storage_service=storage_service,
    websocket_client=websocket_client,
    http_client=http_client,
    log_service=log_service,
)

# Create message
message = service.create_message(
    plaintext_content=b"Hello, world!",
    recipients=["recipient-001", "recipient-002"],
    conversation_id="conv-001",
    expiration_days=7,  # Default
)

# Send message
service.send_message(message)

# Receive message
received = service.receive_message(
    message_id=message_id,
    encrypted_payload=encrypted_payload,
    sender_id="sender-001",
    conversation_id="conv-001",
    expiration_timestamp=expiration_timestamp,
)

# Process offline queue (call on network reconnection)
service.process_offline_queue()

# Cleanup expired messages (call on app start/reconnection)
service.cleanup_expired_messages()
```

## Deterministic Rules

All behavior follows resolved TBDs and clarifications:

1. **Message Expiration**: Default 7 days, enforced device-locally
2. **Offline Storage**: Max 500 messages or 50MB, eviction only for expired
3. **Retry Limits**: Maximum 5 attempts before marking as Failed
4. **Duplicate Detection**: Message ID first, content hash secondary
5. **Expiration Enforcement**: Immediate deletion, no grace period
6. **Delivery Mechanism**: WebSocket preferred, REST polling fallback every 30s

## References

- Functional Specification (#6)
- State Machines (#7)
- Data Classification & Retention (#8)
- API Contracts (#10)
- Lifecycle Playbooks (#15)
- Resolved Specs & Clarifications
