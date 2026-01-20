# Device Identity Lifecycle Diagrams

**References:**
- Identity Provisioning (#11)
- State Machines (#7), Section 5
- Functional Specification (#6), Section 3.1
- Lifecycle Playbooks (#15)
- Resolved Specs & Clarifications

## Device Identity Lifecycle State Machine

```mermaid
stateDiagram-v2
    [*] --> Pending: Controller initiates provisioning<br/>POST /api/device/provision<br/>Generate device_id, key pair
    
    Pending --> Provisioned: Device receives provisioning data<br/>Store keys in secure keystore
    
    Provisioned --> Active: Device confirms provisioning<br/>POST /api/device/provision/confirm<br/>Activate device identity
    
    Active --> Active: Normal operation<br/>Send/receive messages<br/>Create/join conversations
    
    Active --> Revoked: Controller revokes device<br/>POST /api/device/revoke<br/>Mark identity revoked<br/>Trigger key rotation
    
    Revoked --> Revoked: Neutral enterprise mode<br/>Read historical conversations<br/>Cannot send/create/join
    
    Revoked --> [*]: Device factory reset<br/>Identity destroyed<br/>Decommissioned
    
    note right of Pending
        Only Controllers can initiate provisioning
        Device identity consists of:
        - device_id (UUID)
        - Public/private key pair
        - Provisioning metadata
    end note
    
    note right of Active
        Device can:
        - Send messages
        - Create/join conversations
        - Read conversations
        Normal messaging operation
    end note
    
    note right of Revoked
        Revocation is immediate and irreversible
        Device can:
        - Read historical conversations (neutral enterprise mode)
        Cannot:
        - Send messages
        - Create/join conversations
        Key rotation triggered immediately
    end note
```

## Device Provisioning Flow

```mermaid
sequenceDiagram
    participant Controller
    participant Backend as Backend API
    participant Registry as Device Registry
    participant Device
    
    Controller->>Backend: POST /api/device/provision<br/>{device_id, public_key}
    Backend->>Registry: register_device(device_id, public_key)
    Registry->>Registry: Create DeviceIdentity in Pending state
    Registry-->>Backend: DeviceIdentity (Pending)
    Backend->>Device: Send encrypted provisioning payload
    Device->>Device: Store keys in secure keystore
    Device->>Backend: POST /api/device/provision/confirm
    Backend->>Registry: confirm_provisioning(device_id)
    Registry->>Registry: Transition Provisioned → Active
    Registry-->>Backend: Success
    Backend-->>Device: {status: "confirmed"}
    Device->>Device: Enable messaging features
    Device->>Device: UI: "Device successfully provisioned"
    
    Note over Registry: Device now in Active state<br/>Can send messages and create/join conversations
```

## Device Revocation Flow

```mermaid
sequenceDiagram
    participant Controller
    participant Backend as Backend API
    participant Registry as Device Registry
    participant Enforcement as Identity Enforcement
    participant ConvRegistry as Conversation Registry
    participant Device
    
    Controller->>Backend: POST /api/device/revoke<br/>{device_id}
    Backend->>Registry: revoke_device(device_id)
    Registry->>Registry: Transition Active → Revoked
    Registry->>Registry: Trigger key rotation immediately
    Registry-->>Backend: Success
    
    Backend->>Enforcement: handle_revocation_impact(device_id)
    Enforcement->>ConvRegistry: handle_participant_revocation(device_id)
    ConvRegistry->>ConvRegistry: Remove device from all conversations
    ConvRegistry->>ConvRegistry: Close conversations if all participants revoked
    ConvRegistry-->>Enforcement: Affected conversations list
    Enforcement-->>Backend: Revocation impact summary
    
    Backend->>Device: Send revocation notice
    Device->>Device: Delete all secure local data (messages, keys)
    Device->>Device: Disable messaging features
    Device->>Device: UI: "Messaging Disabled"
    
    Note over Registry,Device: Revocation is immediate and irreversible<br/>Device enters neutral enterprise mode<br/>Can read historical conversations only
```

## Key Rotation Flow

```mermaid
sequenceDiagram
    participant System
    participant Registry as Device Registry
    participant Device
    
    alt Scheduled Rotation (90 days)
        System->>Registry: get_devices_needing_key_rotation()
        Registry->>Registry: Check next_key_rotation timestamps
        Registry-->>System: List of devices needing rotation
        System->>Device: Request key rotation
        Device->>Device: Generate new key pair
        Device->>System: POST /api/device/rotate<br/>{device_id, new_public_key}
        System->>Registry: rotate_device_key(device_id, new_public_key)
        Registry->>Registry: Update public_key
        Registry->>Registry: Update last_key_rotation
        Registry->>Registry: Schedule next rotation (90 days)
        Registry-->>System: Success
    else Immediate Rotation (on revocation)
        System->>Registry: revoke_device(device_id)
        Registry->>Registry: Transition to Revoked
        Registry->>Registry: Update last_key_rotation = revoked_at
        Registry->>Registry: Clear next_key_rotation (no scheduled rotations)
        Registry-->>System: Revocation complete
    end
    
    Note over Registry: Key rotation occurs:
    - Every 90 days (scheduled)
    - Immediately upon revocation
    per Resolved TBDs
```

## Identity Enforcement Flow

```mermaid
flowchart TD
    A[API Request Received] --> B{Extract device_id from<br/>X-Device-ID header}
    B --> C{Operation Type}
    
    C -->|Send Message| D[enforce_message_sending]
    C -->|Create Conversation| E[enforce_conversation_creation]
    C -->|Join Conversation| F[enforce_conversation_join]
    C -->|Read Conversation| G[enforce_conversation_read]
    
    D --> H{Device Active?}
    E --> H
    F --> H
    G --> I{Device Active or Revoked?}
    
    H -->|Yes| J[Allow Operation]
    H -->|No| K{Device Revoked?}
    
    K -->|Yes| L[Return 403 Forbidden]
    K -->|No| M[Return 401 Unauthorized]
    
    I -->|Yes| J
    I -->|No| M
    
    J --> N[Process Request]
    L --> O[Log Warning]
    M --> O
    
    style J fill:#ccffcc
    style L fill:#ffcccc
    style M fill:#ffcccc
    style N fill:#ccffcc
    style O fill:#ffffcc
    
    note1[Server-side enforcement only<br/>Client behavior is advisory<br/>per Resolved Clarifications]
```

## Revocation Impact on Conversations

```mermaid
flowchart TD
    A[Device Revoked] --> B[handle_revocation_impact]
    B --> C[Get all conversations for device]
    C --> D{For each conversation}
    
    D --> E[Remove device from participants]
    E --> F{Other participants remain?}
    
    F -->|Yes| G[Conversation remains Active]
    F -->|No| H[Close conversation]
    
    G --> I[Device can still read<br/>historical messages]
    H --> I
    
    I --> J[Neutral Enterprise Mode]
    J --> K[Device cannot:<br/>- Send messages<br/>- Create conversations<br/>- Join conversations]
    K --> L[Device can:<br/>- Read historical conversations]
    
    style A fill:#ffcccc
    style H fill:#ffcccc
    style J fill:#ffffcc
    style L fill:#ccffcc
    
    note1[Revocation impact per State Machines #7, Section 4<br/>All messages remain until expiration<br/>No new messages accepted in closed conversations]
```

## Permission Matrix

```mermaid
graph LR
    subgraph "Device States"
        P[Pending]
        Pr[Provisioned]
        A[Active]
        R[Revoked]
    end
    
    subgraph "Permissions"
        S[Send Messages]
        C[Create Conversations]
        J[Join Conversations]
        Re[Read Conversations]
    end
    
    P -->|None| S
    Pr -->|None| S
    A -->|Allowed| S
    R -->|Denied| S
    
    P -->|None| C
    Pr -->|None| C
    A -->|Allowed| C
    R -->|Denied| C
    
    P -->|None| J
    Pr -->|None| J
    A -->|Allowed| J
    R -->|Denied| J
    
    P -->|None| Re
    Pr -->|None| Re
    A -->|Allowed| Re
    R -->|Allowed| Re
    
    style A fill:#ccffcc
    style R fill:#ffcccc
    style S fill:#ffffcc
    style C fill:#ffffcc
    style J fill:#ffffcc
    style Re fill:#ccffcc
    
    note1[Permission matrix per Resolved Clarifications #38<br/>Revoked devices can read (neutral enterprise mode)<br/>All enforcement is server-side]
```

## Key Deterministic Rules

1. **State Transitions**: Pending → Provisioned → Active → Revoked per State Machines (#7), Section 5
2. **Revocation**: Immediate and irreversible per Identity Provisioning (#11), Section 5
3. **Key Rotation**: Every 90 days or immediately upon revocation per Resolved TBDs
4. **Permission Enforcement**: Server-side only; client behavior is advisory per Resolved Clarifications
5. **Revoked Device Permissions**:
   - Cannot send messages per Resolved Clarifications (#38)
   - Cannot create or join conversations per Resolved Clarifications (#38)
   - May read historical conversations (neutral enterprise mode) per Resolved Clarifications (#38)
6. **No Message Delivery**: No messages may be delivered from revoked or expired devices per Functional Spec (#6)
7. **Controller Authority**: Only Controllers can move devices between states per State Machines (#7)
