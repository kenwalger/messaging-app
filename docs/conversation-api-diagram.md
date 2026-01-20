# Conversation API Lifecycle Diagrams

**References:**
- Functional Specification (#6), Section 4.1
- State Machines (#7), Section 4
- API Contracts (#10)
- Identity Provisioning (#11)
- Resolved Specs & Clarifications

## Conversation Lifecycle State Machine

```mermaid
stateDiagram-v2
    [*] --> Uncreated: Conversation not yet created
    
    Uncreated --> Active: POST /api/conversation/create<br/>Operator initiates conversation<br/>Create conversation object<br/>Assign participants (max 50)
    
    Active --> Active: POST /api/conversation/join<br/>Participant joins<br/>(if under max group size)
    
    Active --> Active: POST /api/conversation/leave<br/>Participant leaves<br/>(if other participants remain)
    
    Active --> Closed: POST /api/conversation/close<br/>Participant closes conversation<br/>OR<br/>All participants leave/revoked
    
    Closed --> [*]: Conversation removed from registry
    
    note right of Uncreated
        No implicit conversation discovery
        Explicit creation only
        Participants explicitly defined
        Only provisioned devices may create
    end note
    
    note right of Active
        Max 50 participants per Resolved TBDs
        Messages can be sent
        Participants can join/leave
        Only provisioned devices may join
    end note
    
    note right of Closed
        All messages remain until expiration
        No new messages accepted
        Cannot be resurrected
        Removed from registry per Data Classification (#8)
    end note
```

## Conversation Creation Flow

```mermaid
sequenceDiagram
    participant Device as Provisioned Device
    participant API as Conversation API
    participant Registry as Conversation Registry
    participant DevReg as Device Registry
    participant Log as Log Service
    
    Device->>API: POST /api/conversation/create<br/>{participants: [...]}
    API->>DevReg: Validate device active
    DevReg-->>API: Device active (provisioned)
    API->>API: Validate group size (max 50)
    API->>DevReg: Validate all participants active
    DevReg-->>API: All participants valid
    API->>Registry: register_conversation()
    Registry->>Registry: Create in Active state
    Registry-->>API: Success
    API->>Log: Log conversation_created event
    API-->>Device: {status: "success", conversation_id, state: "active"}
    
    Note over API,Registry: Conversation in Active state<br/>Can accept messages and participants
```

## Participant Join Flow

```mermaid
sequenceDiagram
    participant Device as Provisioned Device
    participant API as Conversation API
    participant Registry as Conversation Registry
    participant DevReg as Device Registry
    
    Device->>API: POST /api/conversation/join<br/>{conversation_id}
    API->>DevReg: Validate device active
    DevReg-->>API: Device active
    API->>Registry: Check conversation active
    Registry-->>API: Conversation active
    API->>Registry: Check group size limit
    Registry-->>API: Under limit (can join)
    API->>Registry: add_participant()
    Registry->>Registry: Add participant
    Registry-->>API: Success
    API-->>Device: {status: "success"}
    
    alt Max Group Size Reached
        Registry-->>API: Limit exceeded
        API-->>Device: {status: "error", error_code: 400,<br/>message: "Max group size reached"}
    end
    
    alt Conversation Closed
        Registry-->>API: Conversation closed
        API-->>Device: {status: "error", error_code: 404,<br/>message: "Conversation not found or closed"}
    end
```

## Participant Leave Flow

```mermaid
sequenceDiagram
    participant Device as Participant Device
    participant API as Conversation API
    participant Registry as Conversation Registry
    
    Device->>API: POST /api/conversation/leave<br/>{conversation_id}
    API->>Registry: Check if participant
    Registry-->>API: Is participant
    API->>Registry: remove_participant()
    Registry->>Registry: Remove participant
    
    alt Other Participants Remain
        Registry->>Registry: Conversation remains Active
        Registry-->>API: Participant removed
        API-->>Device: {status: "success"}
    else All Participants Removed
        Registry->>Registry: Transition to Closed
        Registry-->>API: Conversation closed
        API-->>Device: {status: "success",<br/>conversation_closed: true}
    end
```

## Conversation Close Flow

```mermaid
sequenceDiagram
    participant Device as Participant Device
    participant API as Conversation API
    participant Registry as Conversation Registry
    participant Log as Log Service
    
    Device->>API: POST /api/conversation/close<br/>{conversation_id}
    API->>Registry: Check if participant
    Registry-->>API: Is participant
    API->>Registry: Check conversation state
    Registry-->>API: Conversation Active
    API->>Registry: close_conversation()
    Registry->>Registry: Transition Active -> Closed
    Registry-->>API: Success
    API->>Log: Log conversation_closed event
    API-->>Device: {status: "success", state: "closed"}
    
    Note over Registry: All messages remain until expiration<br/>No new messages accepted<br/>per Resolved Clarifications (#36)
```

## Permission Enforcement Flow

```mermaid
flowchart TD
    A[API Request Received] --> B{Extract device_id from<br/>X-Device-ID header}
    B --> C{Check device active?<br/>DeviceRegistry.is_device_active}
    
    C -->|Active| D{Operation Type}
    C -->|Revoked/Invalid| E[Return 403 Forbidden]
    
    D -->|Create Conversation| F{Validate all participants<br/>are provisioned}
    F -->|Valid| G[Create Conversation]
    F -->|Invalid| H[Return 400 Bad Request]
    
    D -->|Join Conversation| I{Check conversation active<br/>and under max size}
    I -->|Valid| J[Join Conversation]
    I -->|Invalid| K[Return 400/404 Error]
    
    D -->|Leave/Close| L{Check if participant}
    L -->|Yes| M[Perform Operation]
    L -->|No| N[Return 403/404 Error]
    
    G --> O[Return 200 Success]
    J --> O
    M --> O
    
    style E fill:#ffcccc
    style H fill:#ffcccc
    style K fill:#ffcccc
    style N fill:#ffcccc
    style O fill:#ccffcc
```

## Neutral Enterprise Mode Flow

```mermaid
flowchart TD
    A[Revoked Device Request] --> B{Operation Type}
    
    B -->|Create Conversation| C[Block: Return 403]
    B -->|Join Conversation| C
    B -->|Send Message| C
    B -->|View Conversation Info| D[Allow: Neutral Enterprise Mode]
    B -->|Read Historical Messages| D
    
    D --> E[Return Conversation Info<br/>Read-only access]
    
    style C fill:#ffcccc
    style D fill:#ffffcc
    style E fill:#ccffcc
    
    note1[Revoked devices can read/view<br/>but cannot create/join/send<br/>per Resolved Clarifications #38]
```

## Key Deterministic Rules

1. **Permission Enforcement**: Only provisioned devices (Active state) may create or join conversations per Identity Provisioning (#11)
2. **Group Size Limit**: Max 50 participants per conversation per Resolved TBDs
3. **State Transitions**: Uncreated → Active → Closed per State Machines (#7), Section 4
4. **Conversation Closure**: All messages remain until expiration; no new messages accepted per Resolved Clarifications (#36)
5. **Participant Management**: Participants can join/leave; conversation closes if all leave per State Machines (#7), Section 4
6. **Neutral Enterprise Mode**: Revoked devices can view but cannot create/join per Resolved Clarifications (#38)
7. **Explicit Creation**: No auto-discovery; conversations must be explicitly created per State Machines (#7)
8. **Closed Conversations**: Cannot be resurrected per State Machines (#7)
