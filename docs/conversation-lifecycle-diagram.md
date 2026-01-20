# Conversation Lifecycle State Diagram

**References:**
- State Machines (#7), Section 4
- Functional Specification (#6), Section 4.1
- Data Classification & Retention (#8), Section 3
- Resolved Specs & Clarifications

## Conversation Lifecycle State Machine

```mermaid
stateDiagram-v2
    [*] --> Uncreated: Conversation not yet created
    
    Uncreated --> Active: Operator initiates conversation<br/>Create conversation object<br/>Assign participants (max 50)
    
    Active --> Active: Participant revoked<br/>Remove participant<br/>(if other participants remain)
    
    Active --> Closed: All participants leave or revoked<br/>Delete conversation object
    
    Closed --> [*]: Conversation removed from storage
    
    note right of Uncreated
        No implicit conversation discovery
        Explicit creation only
        Participants explicitly defined
    end note
    
    note right of Active
        Max 50 participants per Resolved TBDs
        Messages can be sent
        Participants can be added/removed
    end note
    
    note right of Closed
        All messages remain until expiration
        No new messages accepted
        Cannot be resurrected
        Removed from storage per Data Classification (#8)
    end note
```

## Conversation Creation Flow

```mermaid
sequenceDiagram
    participant Operator as Operator Device
    participant Manager as Conversation Manager
    participant Registry as Device Registry
    participant Log as Log Service
    
    Operator->>Manager: create_conversation(participants)
    Manager->>Manager: Validate group size (max 50)
    Manager->>Registry: Validate participant devices
    Registry-->>Manager: Active devices confirmed
    Manager->>Manager: Generate conversation_id (UUID)
    Manager->>Manager: Create Conversation (Active state)
    Manager->>Log: Log conversation_created event
    Manager-->>Operator: Conversation object
    
    Note over Manager: Conversation in Active state<br/>Can accept messages
```

## Participant Management Flow

```mermaid
sequenceDiagram
    participant Manager as Conversation Manager
    participant Conversation as Conversation Object
    participant Registry as Device Registry
    
    Manager->>Conversation: add_participant(device_id)
    Conversation->>Conversation: Check state (must be Active)
    Conversation->>Conversation: Check group size (max 50)
    Conversation->>Registry: Validate device active
    Registry-->>Conversation: Device valid
    Conversation->>Conversation: Add participant
    Conversation-->>Manager: Success
    
    Note over Manager,Conversation: Participant added<br/>Conversation remains Active
    
    Manager->>Conversation: remove_participant(device_id)
    Conversation->>Conversation: Remove participant
    alt Other participants remain
        Conversation-->>Manager: Success (Active)
    else All participants removed
        Conversation->>Conversation: Transition to Closed
        Conversation-->>Manager: Success (Closed)
    end
```

## Conversation Closure Flow

```mermaid
flowchart TD
    A[Active Conversation] --> B{All Participants Revoked?}
    B -->|Yes| C[Close Conversation]
    B -->|No| D[Remove Participant]
    D --> E{Other Participants Remain?}
    E -->|Yes| A
    E -->|No| C
    
    C --> F[Transition to Closed State]
    F --> G[Messages Remain Until Expiration]
    G --> H[No New Messages Accepted]
    H --> I[Conversation Removed from Storage]
    
    style C fill:#ffcccc
    style F fill:#ffcccc
    style I fill:#ffcccc
```

## Neutral Enterprise Mode Flow

```mermaid
flowchart TD
    A[Device Active] --> B[Device Revoked]
    B --> C[Enter Neutral Enterprise Mode]
    C --> D{Action Attempted}
    
    D -->|Read Messages| E[Allowed]
    D -->|View Conversation List| E
    D -->|Send Message| F[Blocked]
    D -->|Create Conversation| F
    D -->|Modify Conversation| F
    
    E --> G[Continue in Read-Only Mode]
    F --> H[Show: Messaging Disabled]
    
    style C fill:#ffffcc
    style F fill:#ffcccc
    style H fill:#ffcccc
```

## Key Deterministic Rules

1. **Conversation Creation**: Explicit only, no auto-discovery per State Machines (#7)
2. **Group Size Limit**: Max 50 participants per Resolved TBDs
3. **State Transitions**: Uncreated → Active → Closed per State Machines (#7)
4. **Closure Behavior**: All messages remain until expiration; no new messages accepted per Resolved Clarifications
5. **Participant Revocation**: Removes participant; closes conversation if all revoked per State Machines (#7)
6. **Neutral Enterprise Mode**: Read-only access for revoked devices per Resolved Clarifications
7. **Data Classification**: Conversation membership is Restricted; removed when conversation ends per Data Classification (#8)
