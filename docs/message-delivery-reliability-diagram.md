# Message Delivery Reliability & Hardening Diagrams

**References:**
- Functional Specification (#6), Sections 4.2-4.5
- State Machines (#7), Section 3
- Lifecycle Playbooks (#15), Section 5
- Resolved Specs & Clarifications (#51)
- API Contracts (#10)

## Message Delivery Lifecycle with ACK

```mermaid
sequenceDiagram
    participant Client as Client Device
    participant WS as WebSocket
    participant Backend as Backend Relay
    participant Recipient as Recipient Device
    
    Client->>WS: Send message (PENDING_DELIVERY)
    WS->>Backend: Forward encrypted message
    Backend->>Recipient: Deliver message
    Recipient->>Backend: ACK received
    Backend->>WS: ACK forwarded
    WS->>Client: Delivery ACK
    Client->>Client: Transition to DELIVERED
    
    Note over Client: ACK timeout (30s) triggers retry<br/>with exponential backoff
    
    alt ACK Timeout
        Client->>Client: ACK timeout detected
        Client->>Client: Retry with exponential backoff
        Client->>WS: Retry message delivery
    end
    
    alt Max Retries Exceeded
        Client->>Client: Mark as FAILED
        Client->>Client: Log delivery failure
    end
```

## Retry & Failure State Transitions

```mermaid
stateDiagram-v2
    [*] --> Created: Message created
    
    Created --> PendingDelivery: send_message()
    
    PendingDelivery --> PendingDelivery: ACK timeout<br/>Retry with backoff<br/>(if retry_count < 5)
    
    PendingDelivery --> Delivered: ACK received<br/>per Resolved Clarifications (#51)
    
    PendingDelivery --> Failed: Max retries exceeded<br/>(5 attempts per Resolved TBDs)
    
    Delivered --> Active: Message received<br/>and decrypted
    
    Active --> Expired: Expiration timer<br/>reached per State Machines (#7)
    
    Failed --> Expired: After expiration<br/>timestamp
    
    Expired --> [*]: Message deleted
    
    note right of PendingDelivery
        Exponential backoff:
        delay = min(base * 2^retry_count, max)
        base = 1s, max = 60s
    end note
    
    note right of Failed
        Logged per Logging & Observability (#14)
        Content-free logging only
    end note
```

## WebSocket Reconnect & REST Fallback Flow

```mermaid
flowchart TD
    A[WebSocket Connected] --> B[WebSocket Disconnect]
    B --> C[Start Exponential Backoff Reconnect]
    C --> D{Reconnect Successful?}
    
    D -->|Yes| E[Stop REST Polling]
    E --> A
    
    D -->|No| F{Timeout > 15s?}
    F -->|No| C
    F -->|Yes| G[Start REST Polling Fallback]
    
    G --> H[Poll /api/message/receive every 30s]
    H --> I{WebSocket Reconnected?}
    I -->|Yes| E
    I -->|No| H
    
    style B fill:#ffcccc
    style G fill:#ffffcc
    style E fill:#ccffcc
```

## Exponential Backoff Retry Flow

```mermaid
flowchart TD
    A[Message Send Failed] --> B[Calculate Backoff Delay]
    B --> C[delay = base * 2^retry_count]
    C --> D{delay > max?}
    D -->|Yes| E[delay = max 60s]
    D -->|No| F[Use calculated delay]
    E --> G[Schedule Retry Timer]
    F --> G
    G --> H[Wait for Backoff Period]
    H --> I[Attempt Delivery]
    I --> J{Success?}
    J -->|Yes| K[Mark as DELIVERED]
    J -->|No| L{retry_count < 5?}
    L -->|Yes| M[Increment retry_count]
    M --> B
    L -->|No| N[Mark as FAILED]
    
    style N fill:#ffcccc
    style K fill:#ccffcc
```

## REST Polling Message Processing

```mermaid
sequenceDiagram
    participant Polling as REST Polling Thread
    participant Backend as Backend API
    participant Service as Message Delivery Service
    participant Storage as Storage Service
    
    loop Every 30 seconds
        Polling->>Backend: GET /api/message/receive
        Backend-->>Polling: {messages: [...]}
        
        loop For each message
            Polling->>Service: receive_message()
            Service->>Service: Check expiration
            alt Expired
                Service-->>Polling: Reject (None)
            else Not Expired
                Service->>Service: Check duplicate (Message ID)
                alt Duplicate ID
                    Service-->>Polling: Reject (None)
                else Unique ID
                    Service->>Service: Check duplicate (Content Hash)
                    alt Duplicate Hash
                        Service-->>Polling: Reject (None)
                    else Unique
                        Service->>Service: Decrypt payload
                        Service->>Storage: Store encrypted
                        Service->>Service: Start expiration timer
                        Service-->>Polling: Message received
                    end
                end
            end
        end
    end
    
    Note over Polling: Stops when WebSocket reconnects<br/>per Resolved TBDs (#18)
```

## ACK Timeout Handling

```mermaid
sequenceDiagram
    participant Service as Message Delivery Service
    participant Timer as ACK Timeout Timer
    participant Message as Message Object
    
    Service->>Service: Send message via WebSocket
    Service->>Service: Track pending ACK
    Service->>Timer: Start ACK timeout (30s)
    
    alt ACK Received
        Service->>Service: handle_delivery_ack()
        Service->>Message: Transition to DELIVERED
        Service->>Service: Remove from pending ACKs
        Timer->>Timer: Cancel timeout
    else ACK Timeout
        Timer->>Service: _handle_ack_timeout()
        Service->>Service: Remove from pending ACKs
        Service->>Service: Check expiration
        alt Expired
            Service->>Message: Mark as EXPIRED
        else Not Expired
            Service->>Service: Check retry_count
            alt retry_count < 5
                Service->>Service: Retry with exponential backoff
            else retry_count >= 5
                Service->>Message: Mark as FAILED
                Service->>Service: Log delivery failure
            end
        end
    end
```

## Key Deterministic Rules

1. **ACK Handling**: Per Resolved Clarifications (#51)
   - ACK per message ID
   - 30s timeout
   - Retry on timeout with exponential backoff

2. **Retry Policy**: Per Lifecycle Playbooks (#15) and Resolved TBDs (#19)
   - Max 5 attempts
   - Exponential backoff: base * 2^retry_count (capped at 60s)
   - Mark as FAILED after max retries

3. **Expiration Rules**: Per Functional Spec (#6), Section 4.4
   - Do not deliver expired messages
   - Remove expired messages from queue immediately
   - Expired messages cannot be recovered

4. **WebSocket Lifecycle**: Per Resolved Clarifications (#51)
   - Reconnect with exponential backoff
   - Fallback to REST polling if disconnected >15s
   - Stop REST polling when WebSocket reconnects

5. **REST Polling**: Per Resolved TBDs (#18)
   - Poll every 30 seconds
   - Respect expiration and duplicate detection
   - Only active when WebSocket unavailable

6. **Duplicate Detection**: Per Resolved Clarifications (#35)
   - Primary: Message ID comparison
   - Secondary: Content hash comparison
   - Silently discard duplicates
