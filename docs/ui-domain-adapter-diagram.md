# UI Domain Adapter Layer Diagrams

**References:**
- UX Behavior (#12)
- Copy Rules (#13)
- Functional Specification (#6)
- Client-Facing API Boundary (latest)
- Resolved Specs & Clarifications

## API → UI Domain Mapping Flow

```mermaid
flowchart TD
    subgraph "Client API Layer"
        A[ClientMessageDTO] -->|Map| B[UIAdapter]
        C[ClientConversationDTO] -->|Map| B
        D[Device State] -->|Map| B
    end
    
    subgraph "UI Adapter Layer"
        B -->|Derive Flags| E[MessageViewModel]
        B -->|Derive Flags| F[ConversationViewModel]
        B -->|Derive Flags| G[DeviceStateViewModel]
        
        E -->|is_expired| H[Expiration Check]
        E -->|is_failed| I[Failure Check]
        E -->|is_read_only| J[Read-Only Mode]
        
        F -->|can_send| K[Send Permission]
        F -->|send_disabled| L[Send Disabled]
        F -->|is_read_only| J
        
        G -->|can_send| K
        G -->|can_create_conversations| M[Create Permission]
        G -->|can_join_conversations| N[Join Permission]
        G -->|is_read_only| J
    end
    
    subgraph "UI Domain Models"
        E
        F
        G
        O[ParticipantViewModel]
    end
    
    subgraph "UI Layer"
        E -->|Render| P[Message Display]
        F -->|Render| Q[Conversation List]
        G -->|Render| R[Device Status]
        O -->|Render| S[Participant Display]
    end
    
    style B fill:#ccffcc
    style E fill:#ccffcc
    style F fill:#ccffcc
    style G fill:#ccffcc
    style J fill:#ffffcc
    style K fill:#ccffcc
    style L fill:#ffcccc
    
    note1[UI adapter layer:<br/>- Stateless beyond derived fields<br/>- Deterministically derived from API responses<br/>- No internal IDs, retry counters, or cryptographic internals<br/>per UX Behavior #12]
```

## Message View Model Derivation

```mermaid
flowchart LR
    A[ClientMessageDTO] -->|Input| B[UIAdapter.map_message_to_view_model]
    
    B -->|Check| C{expires_at < current_time?}
    C -->|Yes| D[is_expired = true]
    C -->|No| E[is_expired = false]
    
    B -->|Check| F{state == FAILED?}
    F -->|Yes| G[is_failed = true]
    F -->|No| H[is_failed = false]
    
    B -->|Parameter| I{is_read_only?}
    I -->|Yes| J[is_read_only = true]
    I -->|No| K[is_read_only = false]
    
    D -->|Combine| L[MessageViewModel]
    E -->|Combine| L
    G -->|Combine| L
    H -->|Combine| L
    J -->|Combine| L
    K -->|Combine| L
    
    L -->|Output| M[UI Domain Model]
    
    style B fill:#ccffcc
    style L fill:#ccffcc
    style M fill:#ccffcc
    style D fill:#ffcccc
    style G fill:#ffcccc
    style J fill:#ffffcc
    
    note1[Message view model derivation per UX Behavior #12, Section 3.3 and 3.4<br/>Expired and failed messages are explicitly distinguishable]
```

## Conversation View Model Derivation

```mermaid
flowchart LR
    A[ClientConversationDTO] -->|Input| B[UIAdapter.map_conversation_to_view_model]
    
    B -->|Check| C{is_read_only?}
    C -->|Yes| D[is_read_only = true]
    C -->|No| E[is_read_only = false]
    
    B -->|Check| F{state == ACTIVE?}
    F -->|Yes| G[Active State]
    F -->|No| H[Closed State]
    
    D -->|Combine| I{Derive can_send}
    E -->|Combine| I
    G -->|Combine| I
    H -->|Combine| I
    
    I -->|Logic| J[can_send = !is_read_only && ACTIVE]
    I -->|Logic| K[send_disabled = is_read_only || CLOSED]
    
    J -->|Combine| L[ConversationViewModel]
    K -->|Combine| L
    D -->|Combine| L
    E -->|Combine| L
    
    L -->|Output| M[UI Domain Model]
    
    style B fill:#ccffcc
    style L fill:#ccffcc
    style M fill:#ccffcc
    style D fill:#ffffcc
    style K fill:#ffcccc
    
    note1[Conversation view model derivation per Resolved Clarifications #38<br/>Neutral enterprise mode: readOnly = true, sendDisabled = true]
```

## Device State View Model Derivation

```mermaid
flowchart LR
    A[Device State] -->|Input| B[UIAdapter.map_device_state_to_view_model]
    
    B -->|Parameter| C{is_read_only?}
    C -->|Yes| D[is_read_only = true]
    C -->|No| E[is_read_only = false]
    
    D -->|Derive| F[can_send = false]
    D -->|Derive| G[can_create_conversations = false]
    D -->|Derive| H[can_join_conversations = false]
    
    E -->|Derive| I[can_send = true]
    E -->|Derive| J[can_create_conversations = true]
    E -->|Derive| K[can_join_conversations = true]
    
    F -->|Combine| L[DeviceStateViewModel]
    G -->|Combine| L
    H -->|Combine| L
    I -->|Combine| L
    J -->|Combine| L
    K -->|Combine| L
    D -->|Combine| L
    E -->|Combine| L
    
    L -->|Output| M[UI Domain Model]
    
    style B fill:#ccffcc
    style L fill:#ccffcc
    style M fill:#ccffcc
    style D fill:#ffffcc
    style F fill:#ffcccc
    style G fill:#ffcccc
    style H fill:#ffcccc
    
    note1[Device state view model derivation per Resolved Clarifications #38<br/>Revoked devices can read but cannot send/create/join]
```

## Sorting and Filtering Flow

```mermaid
flowchart TD
    A[List of View Models] -->|Input| B{Operation Type}
    
    B -->|Sort Messages| C[sort_messages_reverse_chronological]
    B -->|Sort Conversations| D[sort_conversations_reverse_chronological]
    B -->|Filter Expired| E[filter_expired_messages]
    B -->|Filter Failed| F[filter_failed_messages]
    B -->|Filter Active| G[filter_active_conversations]
    
    C -->|Key: created_at| H[Reverse Chronological<br/>Newest First]
    D -->|Key: sort_key| H
    
    E -->|Remove| I[is_expired == true]
    F -->|Keep| J[is_failed == true]
    G -->|Keep| K[state == ACTIVE]
    
    H -->|Output| L[Sorted List]
    I -->|Output| M[Filtered List]
    J -->|Output| M
    K -->|Output| M
    
    style C fill:#ccffcc
    style D fill:#ccffcc
    style E fill:#ccffcc
    style F fill:#ccffcc
    style G fill:#ccffcc
    style H fill:#ffffcc
    style I fill:#ffcccc
    style J fill:#ffffcc
    style K fill:#ccffcc
    
    note1[Sorting and filtering per Resolved Clarifications #53<br/>Reverse chronological: newest first<br/>Expired messages removed automatically per UX Behavior #12, Section 3.4]
```

## Neutral Enterprise Mode Flow

```mermaid
flowchart TD
    A[Device Revoked] -->|Trigger| B[is_read_only = true]
    
    B -->|Map| C[MessageViewModel]
    B -->|Map| D[ConversationViewModel]
    B -->|Map| E[DeviceStateViewModel]
    
    C -->|Set| F[is_read_only = true]
    
    D -->|Set| G[is_read_only = true]
    D -->|Set| H[can_send = false]
    D -->|Set| I[send_disabled = true]
    
    E -->|Set| J[is_read_only = true]
    E -->|Set| K[can_send = false]
    E -->|Set| L[can_create_conversations = false]
    E -->|Set| M[can_join_conversations = false]
    E -->|Set| N[display_status = "Messaging Disabled"]
    
    F -->|UI| O[Read-Only Message Display]
    G -->|UI| P[Read-Only Conversation View]
    H -->|UI| P
    I -->|UI| P
    J -->|UI| Q[Device Status Display]
    K -->|UI| Q
    L -->|UI| Q
    M -->|UI| Q
    N -->|UI| Q
    
    style B fill:#ffffcc
    style F fill:#ffffcc
    style G fill:#ffffcc
    style I fill:#ffcccc
    style J fill:#ffffcc
    style K fill:#ffcccc
    style L fill:#ffcccc
    style M fill:#ffcccc
    style N fill:#ffffcc
    
    note1[Neutral enterprise mode per Resolved Clarifications #38<br/>Revoked devices can read historical conversations<br/>but cannot send/create/join<br/>Display: "Messaging Disabled" per Copy Rules #13, Section 4]
```

## Expiration and Failure Visibility Flow

```mermaid
sequenceDiagram
    participant API as Client API
    participant Adapter as UIAdapter
    participant ViewModel as MessageViewModel
    participant UI
    
    API->>Adapter: ClientMessageDTO<br/>(state, expires_at)
    Adapter->>Adapter: Check expiration<br/>(expires_at < current_time)
    Adapter->>Adapter: Check failure<br/>(state == FAILED)
    Adapter->>ViewModel: Create with flags<br/>(is_expired, is_failed)
    
    ViewModel->>UI: Display state
    alt Expired Message
        ViewModel->>UI: is_expired = true<br/>display_state = "expired"
        UI->>UI: Remove from view<br/>(automatic, no undo)
    else Failed Message
        ViewModel->>UI: is_failed = true<br/>display_state = "failed"
        UI->>UI: Show failed state<br/>(explicitly distinguishable)
    else Delivered Message
        ViewModel->>UI: is_expired = false<br/>is_failed = false<br/>display_state = "delivered"
        UI->>UI: Show active message
    end
    
    Note over Adapter,ViewModel: Expired and failed messages<br/>are explicitly distinguishable<br/>per UX Behavior #12, Section 3.4 and 3.6
```

## Key Deterministic Rules

1. **Stateless View Models**: UI domain models are stateless beyond derived fields per deterministic rules
2. **Deterministic Derivation**: All UX flags are deterministically derived from API responses
3. **Neutral Enterprise Mode**: Maps to `readOnly = true`, `sendDisabled = true` per Resolved Clarifications (#38)
4. **Expiration Visibility**: Expired messages are explicitly distinguishable and removed automatically per UX Behavior (#12), Section 3.4
5. **Failure Visibility**: Failed messages are explicitly distinguishable per UX Behavior (#12), Section 3.6
6. **Reverse Chronological Ordering**: Newest first per Resolved Clarifications (#53)
7. **No Internal Leakage**: No UI domain model exposes internal IDs, retry counters, or cryptographic internals
8. **Display States**: All display states are deterministic and neutral per Copy Rules (#13), Section 3
