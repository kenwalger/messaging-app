# Observability and Audit Enforcement Diagrams

**References:**
- Logging & Observability (#14)
- Data Classification & Retention (#8)
- Architecture (#9)
- Resolved Specs & Clarifications

## Observability Data Flow

```mermaid
flowchart TD
    subgraph "Operator Device"
        A[App Operations] -->|Operational Events| B[Local Log Queue]
    end
    
    subgraph "Backend Services"
        B -->|Send logs via API| C[Logging Service]
        D[Message Relay] -->|Delivery Events| C
        E[Device Registry] -->|Provisioning/Revocation| C
        F[Conversation API] -->|Conversation Events| C
        G[Identity Enforcement] -->|Policy Events| C
    end
    
    subgraph "Observability Layer"
        C -->|Structured JSON Logs| H[Log Storage]
        C -->|Metrics| I[Metrics Service]
        C -->|Audit Events| J[Audit Event Recorder]
        
        I -->|1-hour Aggregation| K[Metrics Aggregator]
        K -->|Alert Thresholds| L[Alert System]
        
        H -->|90-day Retention| M[Log Purge]
        J -->|90-day Retention| M
    end
    
    subgraph "Monitoring & Audit"
        H -->|Query| N[Dashboard / Audit Interface]
        K -->|Query| N
        J -->|Query| N
        L -->|Alerts| N
    end
    
    style C fill:#ccffcc
    style I fill:#ccffcc
    style J fill:#ccffcc
    style M fill:#ffcccc
    style N fill:#ffffcc
    
    note1[All logs are content-free per Logging & Observability #14<br/>No message content, keys, or sensitive data]
```

## Log Event Lifecycle

```mermaid
sequenceDiagram
    participant Service as Backend Service
    participant LogSvc as Logging Service
    participant Validator as Content Validator
    participant Storage as Log Storage
    participant Audit as Audit Recorder
    
    Service->>LogSvc: log_event(event_type, event_data)
    LogSvc->>Validator: Validate event_data (content-free)
    
    alt Prohibited Content Detected
        Validator-->>LogSvc: ValueError (prohibited content)
        LogSvc-->>Service: Raise exception
    else Valid Content
        Validator-->>LogSvc: Validation passed
        LogSvc->>LogSvc: Create LogEvent (timestamp, classification)
        LogSvc->>Storage: Store log event
        LogSvc->>Audit: Record audit event (if applicable)
        LogSvc->>LogSvc: Log to Python logger
        LogSvc-->>Service: Success
    end
    
    Note over Validator: Prohibited: message_content, keys,<br/>plaintext, large strings (>1000 chars)<br/>per Logging & Observability #14, Section 4
```

## Metrics Aggregation Flow

```mermaid
flowchart TD
    A[Service Records Metric] -->|metric_name, value| B[Metrics Service]
    B -->|Round to hour| C[1-hour Window]
    C -->|Aggregate| D[Window Metrics Storage]
    
    D -->|Query| E[Get Metric Value]
    D -->|Check Thresholds| F[Alert System]
    
    F -->|≥5 failed deliveries| G[Trigger Alert]
    F -->|Below threshold| H[No Alert]
    
    G -->|Alert Details| I[Dashboard / Notification]
    
    J[Purge Old Metrics] -->|>24 hours| D
    J -->|Remove| K[Deleted Metrics]
    
    style B fill:#ccffcc
    style C fill:#ccffcc
    style F fill:#ffffcc
    style G fill:#ffcccc
    style J fill:#ffcccc
    
    note1[Metrics aggregated in 1-hour windows per Resolved TBDs<br/>Alert threshold: ≥5 failed deliveries per Resolved TBDs]
```

## Audit Event Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Created: Service triggers audit event
    
    Created --> Validated: Validate content-free
    Validated --> Recorded: Store in audit log
    
    Recorded --> Recorded: Append-only (immutable)
    Recorded --> Archived: After 90 days
    
    Archived --> Purged: Retention policy
    Purged --> [*]
    
    note right of Created
        Audit events are:
        - Append-only
        - Immutable
        - Content-free
        - Retained 90 days
        per Data Classification #8
    end note
    
    note right of Recorded
        Events include:
        - event_id (UUID)
        - event_type
        - timestamp
        - event_data (content-free)
        - actor_id (device/controller)
    end note
```

## Log Retention and Purge Flow

```mermaid
flowchart TD
    A[Log Event Created] -->|Store| B[Log Storage]
    B -->|Timestamp| C{Check Age}
    
    C -->|< 90 days| D[Retain Log]
    C -->|≥ 90 days| E[Mark for Purge]
    
    F[Purge Job] -->|Scheduled| G[Scan Logs]
    G -->|Find Expired| E
    
    E -->|Delete| H[Purged Logs]
    D -->|Query| I[Available for Audit]
    
    J[Audit Events] -->|Same Process| B
    
    style B fill:#ccffcc
    style D fill:#ccffcc
    style E fill:#ffcccc
    style H fill:#ffcccc
    style F fill:#ffffcc
    
    note1[Log retention: 90 days per Resolved TBDs<br/>Automatic purge after retention period<br/>per Data Classification #8, Section 4]
```

## Alert Threshold Flow

```mermaid
sequenceDiagram
    participant Service as Service
    participant Metrics as Metrics Service
    participant Aggregator as Metrics Aggregator
    participant Threshold as Alert Threshold Check
    participant Alert as Alert System
    participant Dashboard as Dashboard
    
    Service->>Metrics: record_failed_delivery(message_id)
    Metrics->>Aggregator: Increment failed_deliveries (current window)
    Aggregator->>Aggregator: Aggregate in 1-hour window
    
    Metrics->>Threshold: check_alert_thresholds()
    Threshold->>Threshold: Get failed_deliveries count
    
    alt Count ≥ 5
        Threshold->>Alert: Trigger alert
        Alert->>Alert: Create alert record
        Alert->>Dashboard: Send alert notification
        Alert-->>Threshold: Alert triggered
    else Count < 5
        Threshold-->>Metrics: No alert
    end
    
    Note over Threshold,Alert: Alert threshold: ≥5 failed deliveries<br/>in 1-hour window per Resolved TBDs
```

## Content Validation Flow

```mermaid
flowchart TD
    A[Event Data Received] -->|Validate| B{Check Prohibited Keys}
    
    B -->|Contains prohibited key| C[Raise ValueError]
    B -->|No prohibited keys| D{Check Value Sizes}
    
    D -->|String > 1000 chars| C
    D -->|Valid sizes| E{Check Classification}
    
    E -->|Internal| F[Log as Internal]
    E -->|Restricted| G[Log as Restricted]
    
    F -->|Store| H[Log Storage]
    G -->|Store| H
    
    C -->|Error| I[Reject Event]
    
    style B fill:#ffffcc
    style D fill:#ffffcc
    style C fill:#ffcccc
    style I fill:#ffcccc
    style H fill:#ccffcc
    
    note1[Prohibited keys: content, plaintext, key,<br/>private_key, secret, password, payload<br/>per Logging & Observability #14, Section 4]
```

## Key Deterministic Rules

1. **Content-Free Logging**: No message plaintext, keys, or sensitive data per Logging & Observability (#14), Section 4
2. **Structured JSON**: All logs are structured JSON format with event_type, timestamp, event_data per Logging & Observability (#14), Section 2
3. **Retention**: Operational logs retained for 90 days per Resolved TBDs
4. **Metrics Aggregation**: Metrics aggregated in 1-hour windows per Resolved TBDs
5. **Alert Threshold**: Alert triggered if ≥5 failed deliveries in 1-hour window per Resolved TBDs
6. **Audit Events**: Append-only and immutable per Data Classification (#8), Section 3
7. **Permitted Events**: Only defined event types may be logged per Logging & Observability (#14), Section 3
8. **Deterministic**: Logs only what is defined; every log event has a clear trigger per Logging & Observability (#14), Section 2
