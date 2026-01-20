# Message Lifecycle State Diagram

**References:**
- State Machines (#7), Section 3
- Functional Specification (#6), Sections 4.2-4.5
- Lifecycle Playbooks (#15), Section 5
- Resolved Specs & Clarifications

## Message Lifecycle State Machine

```mermaid
stateDiagram-v2
    [*] --> Created: Operator sends message
    
    Created --> PendingDelivery: Encrypt payload, assign metadata
    
    PendingDelivery --> Delivered: Backend relay receives message
    PendingDelivery --> Failed: Delivery retry exceeds expiration<br/>(max 5 attempts)
    PendingDelivery --> PendingDelivery: Retry delivery<br/>(within expiration window)
    
    Delivered --> Active: Recipient device receives message<br/>Decrypt locally, store securely
    
    Active --> Expired: Expiration timestamp reached<br/>Delete local message, remove from UI
    
    Failed --> Expired: Message discarded
    
    Expired --> [*]: Message irrecoverable
    
    note right of Created
        Message encrypted on device
        UUID v4 generated (client)
        Default expiration: 7 days
    end note
    
    note right of PendingDelivery
        Backend relay stores encrypted payload temporarily
        No plaintext storage
        Metadata: Restricted classification
    end note
    
    note right of Active
        Expiration timer starts immediately
        Device-local enforcement
        Stored encrypted at rest
    end note
    
    note right of Expired
        Deleted from device storage
        Removed from UI
        Cannot be recovered
    end note
```

## Message Delivery Flow

```mermaid
sequenceDiagram
    participant Operator as Operator Device
    participant Client as Message Delivery Service
    participant Queue as Offline Queue
    participant Backend as Backend Relay
    participant Recipient as Recipient Device
    
    Operator->>Client: Create message (plaintext)
    Client->>Client: Encrypt payload on device
    Client->>Client: Generate UUID v4 message ID
    Client->>Client: Set expiration (7 days default)
    
    alt Network Available
        Client->>Backend: Send encrypted payload (WebSocket/REST)
        Backend->>Backend: Validate device identity
        Backend->>Backend: Check expiration timestamp
        Backend->>Recipient: Deliver encrypted payload
        Recipient->>Recipient: Decrypt locally
        Recipient->>Recipient: Store encrypted at rest
        Recipient->>Recipient: Start expiration timer
        Recipient->>Backend: ACK delivery
    else Network Unavailable
        Client->>Queue: Queue encrypted payload
        Note over Queue: Max 500 messages or 50MB<br/>Evict expired only
        Queue->>Client: Process queue on reconnect
        Client->>Backend: Retry delivery (max 5 attempts)
    end
    
    Note over Client,Recipient: Expiration enforced device-locally<br/>Expired messages deleted immediately
```

## Offline Queue Management

```mermaid
flowchart TD
    A[Message Created] --> B{Network Available?}
    B -->|Yes| C[Send via WebSocket/REST]
    B -->|No| D[Queue Offline]
    
    D --> E{Check Storage Limits}
    E -->|Under Limits| F[Add to Queue]
    E -->|Over Limits| G{Expired Messages Exist?}
    
    G -->|Yes| H[Evict Oldest Expired]
    H --> F
    G -->|No| I[Mark as Failed]
    
    F --> J[Wait for Network]
    J --> K{Network Available?}
    K -->|Yes| L[Process Queue]
    K -->|No| M[Check Expiration]
    
    M --> N{Message Expired?}
    N -->|Yes| O[Remove from Queue]
    N -->|No| J
    
    L --> P{Retry Count < 5?}
    P -->|Yes| Q[Attempt Delivery]
    P -->|No| R[Mark as Failed]
    
    Q --> S{Delivery Success?}
    S -->|Yes| T[Remove from Queue]
    S -->|No| U[Increment Retry Count]
    U --> J
    
    style O fill:#ffcccc
    style R fill:#ffcccc
    style T fill:#ccffcc
```

## Duplicate Detection Flow

```mermaid
flowchart TD
    A[Receive Message] --> B{Message Expired?}
    B -->|Yes| C[Reject: Expired]
    B -->|No| D{Message ID Exists?}
    
    D -->|Yes| E[Reject: Duplicate ID]
    D -->|No| F{Content Hash Exists?}
    
    F -->|Yes| G[Reject: Duplicate Content]
    F -->|No| H[Decrypt Payload]
    
    H --> I{Decryption Success?}
    I -->|No| J[Reject: Decryption Failed]
    I -->|Yes| K[Store Encrypted at Rest]
    
    K --> L[Add to Received Tracking]
    L --> M[Start Expiration Timer]
    M --> N[Display in UI]
    
    style C fill:#ffcccc
    style E fill:#ffcccc
    style G fill:#ffcccc
    style J fill:#ffcccc
    style N fill:#ccffcc
```

## Key Deterministic Rules

1. **Message Expiration**: Default 7 days, enforced device-locally per State Machines (#7)
2. **Offline Storage**: Max 500 messages or 50MB, eviction only for expired messages per Resolved Clarifications
3. **Retry Limits**: Maximum 5 attempts before marking as Failed per Resolved TBDs
4. **Duplicate Detection**: Message ID first, content hash secondary per Resolved Clarifications
5. **Expiration Enforcement**: Immediate deletion on expiration, no grace period per Resolved Clarifications
6. **Delivery Mechanism**: WebSocket preferred, REST polling fallback every 30s per Resolved TBDs
