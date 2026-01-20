# API Boundary and Adapter Layer Diagrams

**References:**
- API Contracts (#10)
- UX Behavior (#12)
- Copy Rules (#13)
- Functional Specification (#6)
- Architecture (#9)
- Resolved Specs & Clarifications

## Backend → Client Boundary Flow

```mermaid
flowchart TD
    subgraph "Backend Services"
        A[Message Relay] -->|Internal Message| B[API Adapter]
        C[Conversation API] -->|Internal Conversation| B
        D[Device Registry] -->|Device State| B
        E[Identity Enforcement] -->|Permission Result| B
    end
    
    subgraph "Adapter Layer"
        B -->|Map States| F[State Mapper]
        B -->|Normalize Errors| G[Error Normalizer]
        B -->|Create DTOs| H[DTO Builder]
        F -->|Client States| H
        G -->|Neutral Messages| H
    end
    
    subgraph "Client-Facing API"
        H -->|ClientMessageDTO| I[Message Response]
        H -->|ClientConversationDTO| J[Conversation Response]
        H -->|ClientErrorResponse| K[Error Response]
        H -->|ClientSuccessResponse| L[Success Response]
    end
    
    subgraph "Client"
        I -->|JSON| M[Client App]
        J -->|JSON| M
        K -->|JSON| M
        L -->|JSON| M
    end
    
    style B fill:#ccffcc
    style F fill:#ccffcc
    style G fill:#ccffcc
    style H fill:#ccffcc
    style K fill:#ffcccc
    style L fill:#ccffcc
    
    note1[Adapter layer hides:<br/>- Internal state machine names<br/>- Retry counters<br/>- Cryptographic material<br/>- Internal error stacks<br/>per UX Behavior #12, Section 3.6]
```

## State Mapping Flow

```mermaid
flowchart LR
    subgraph "Internal States"
        A1[MessageState.CREATED] -->|Map| B1[ClientMessageState.SENT]
        A2[MessageState.PENDING_DELIVERY] -->|Map| B1
        A3[MessageState.DELIVERED] -->|Map| B2[ClientMessageState.DELIVERED]
        A4[MessageState.ACTIVE] -->|Map| B2
        A5[MessageState.FAILED] -->|Map| B3[ClientMessageState.FAILED]
        A6[MessageState.EXPIRED] -->|Map| B4[ClientMessageState.EXPIRED]
        
        C1[ConversationState.UNCREATED] -->|Map| D1[ClientConversationState.CLOSED]
        C2[ConversationState.ACTIVE] -->|Map| D2[ClientConversationState.ACTIVE]
        C3[ConversationState.CLOSED] -->|Map| D1
        
        E1[DeviceIdentityState.REVOKED] -->|Map| F1[READ_ONLY Mode]
    end
    
    subgraph "Client-Visible States"
        B1
        B2
        B3
        B4
        D1
        D2
        F1
    end
    
    style A1 fill:#ffffcc
    style A2 fill:#ffffcc
    style A3 fill:#ffffcc
    style A4 fill:#ffffcc
    style A5 fill:#ffffcc
    style A6 fill:#ffffcc
    style B1 fill:#ccffcc
    style B2 fill:#ccffcc
    style B3 fill:#ffcccc
    style B4 fill:#ffcccc
    style F1 fill:#ffffcc
    
    note1[State mapping per UX Behavior #12, Section 4<br/>Clients never see internal state machine names]
```

## Error Normalization Pipeline

```mermaid
flowchart TD
    A[Backend Error/Exception] -->|Catch| B[Error Normalizer]
    B -->|Extract Type| C{Error Type}
    
    C -->|ValueError| D[Map to 400 Invalid Request]
    C -->|KeyError| D
    C -->|PermissionError| E[Map to 401 Unauthorized]
    C -->|RevokedDeviceError| F[Map to 403 Revoked Device]
    C -->|NotFoundError| G[Map to 404 Resource Not Found]
    C -->|Unknown| H[Map to 500 Backend Failure]
    
    D -->|Get Message| I[Copy Rules #13]
    E -->|Get Message| I
    F -->|Get Message| I
    G -->|Get Message| I
    H -->|Get Message| I
    
    I -->|Neutral Message| J[ClientErrorResponse]
    J -->|JSON| K[Client]
    
    style B fill:#ccffcc
    style I fill:#ffffcc
    style J fill:#ffcccc
    style K fill:#ccffcc
    
    note1[Error normalization per Copy Rules #13, Section 4<br/>No technical details, stack traces, or sensitive info<br/>Deterministic, enumerated error codes]
```

## DTO Transformation Flow

```mermaid
sequenceDiagram
    participant Backend as Backend Service
    participant Adapter as API Adapter
    participant Mapper as State Mapper
    participant DTO as DTO Builder
    participant Client
    
    Backend->>Adapter: Internal Message/Conversation
    Adapter->>Mapper: Map internal state
    Mapper->>Mapper: Hide internal details
    Mapper->>DTO: Client-visible state
    DTO->>DTO: Remove sensitive fields
    DTO->>DTO: Add API version (v1)
    DTO->>Client: ClientMessageDTO/ClientConversationDTO
    
    Note over Adapter,DTO: Hidden from client:<br/>- retry_count<br/>- Internal state names<br/>- Cryptographic material<br/>- Participant IDs (count only)<br/>per UX Behavior #12, Section 3.6
```

## API Versioning Flow

```mermaid
flowchart TD
    A[API Request] -->|Extract| B{API Version Header?}
    B -->|Present| C[Validate Version]
    B -->|Missing| D[Default to v1]
    
    C -->|v1| E[Process with v1 Adapter]
    C -->|Unsupported| F[Return 400 Error]
    
    D --> E
    E -->|Response| G[Add api_version: v1]
    G -->|JSON| H[Client]
    
    F -->|Error| H
    
    style E fill:#ccffcc
    style G fill:#ccffcc
    style F fill:#ffcccc
    
    note1[API versioning per API Contracts #10<br/>All responses include api_version field<br/>Default version: v1]
```

## Message Response Flow

```mermaid
sequenceDiagram
    participant Client
    participant API as API Adapter
    participant Backend as Backend Service
    participant Message as Internal Message
    
    Client->>API: GET /api/message/receive
    API->>Backend: Get pending messages
    Backend->>Message: Retrieve messages
    Message-->>Backend: List[Message]
    Backend-->>API: Internal messages
    
    API->>API: map_message_to_dto() for each
    API->>API: Map PENDING_DELIVERY → SENT
    API->>API: Remove retry_count, payload
    API->>API: Add api_version: v1
    
    API-->>Client: {api_version: "v1", messages: [...]}
    
    Note over API: Client never sees:<br/>- retry_count<br/>- Internal state names<br/>- Payload (sent separately)<br/>per API Contracts #10
```

## Error Response Flow

```mermaid
flowchart TD
    A[Backend Operation] -->|Exception| B{Exception Type}
    
    B -->|ValueError| C[400 Invalid Request]
    B -->|PermissionError| D[401 Unauthorized]
    B -->|RevokedDevice| E[403 Revoked Device]
    B -->|NotFoundError| F[404 Resource Not Found]
    B -->|Other| G[500 Backend Failure]
    
    C -->|Get Message| H[Copy Rules Lookup]
    D -->|Get Message| H
    E -->|Get Message| H
    F -->|Get Message| H
    G -->|Get Message| H
    
    H -->|Neutral Message| I[Create ClientErrorResponse]
    I -->|Add Version| J[api_version: v1]
    J -->|JSON| K[Client]
    
    style H fill:#ffffcc
    style I fill:#ffcccc
    style J fill:#ccffcc
    
    note1[Error responses per Copy Rules #13, Section 4<br/>Deterministic, neutral messages only<br/>No technical details or stack traces]
```

## Key Deterministic Rules

1. **State Mapping**: Internal states mapped to client-visible states per UX Behavior (#12), Section 4
2. **No Internal Leakage**: Clients never see retry_count, internal state names, or cryptographic material per UX Behavior (#12), Section 3.6
3. **Error Normalization**: All errors normalized to neutral messages per Copy Rules (#13), Section 4
4. **API Versioning**: All responses include `api_version: v1` per API Contracts (#10)
5. **Deterministic Errors**: Error codes are enumerated and deterministic per API Contracts (#10), Section 6
6. **Content-Free**: No sensitive information in error responses per Copy Rules (#13), Section 4
7. **DTO Transformation**: Internal models transformed to client-safe DTOs hiding implementation details
8. **Read-Only Mode**: Revoked devices mapped to READ_ONLY state per Resolved Clarifications (#38)
