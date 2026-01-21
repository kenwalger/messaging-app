# Controller API Endpoints

## Overview

This document describes the Controller API endpoints for device provisioning and revocation per API Contracts (#10) and Identity Provisioning (#11).

## Endpoints

### POST /api/device/provision

Controller provisions a device with identity and keys. Creates device in Pending state.

### POST /api/device/provision/confirm

Controller confirms device provisioning. Transitions device from Pending → Provisioned state.

### POST /api/device/revoke

Controller revokes device. Revocation is immediate and irreversible. Revoked devices are removed from all conversations and enter neutral enterprise mode (read-only).

## State Transitions

```mermaid
stateDiagram-v2
    [*] --> Pending: POST /api/device/provision
    Pending --> Provisioned: POST /api/device/provision/confirm
    Provisioned --> Active: Device confirms (internal)
    Active --> Revoked: POST /api/device/revoke
    Provisioned --> Revoked: POST /api/device/revoke
    Revoked --> [*]: No reactivation allowed
    
    note right of Pending
        Device created with identity
        and public key
    end note
    
    note right of Provisioned
        Device received provisioning
        data and stored keys
    end note
    
    note right of Active
        Device confirmed provisioning
        and is operational
    end note
    
    note right of Revoked
        Immediate and irreversible
        Removed from conversations
        Read-only access only
    end note
```

## Controller Authentication Flow

```mermaid
sequenceDiagram
    participant Controller
    participant ControllerAPI
    participant ControllerAuth
    participant DeviceRegistry
    participant ConversationRegistry
    participant LoggingService
    
    Controller->>ControllerAPI: POST /api/device/provision<br/>{device_id, public_key}<br/>X-Controller-Key: api-key
    ControllerAPI->>ControllerAuth: validate_controller_key(api-key)
    ControllerAuth-->>ControllerAPI: authorized: true/false
    
    alt Authorized
        ControllerAPI->>DeviceRegistry: register_device(device_id, public_key)
        DeviceRegistry-->>ControllerAPI: DeviceIdentity (Pending state)
        ControllerAPI->>LoggingService: log_audit_event(DEVICE_PROVISIONED)
        ControllerAPI-->>Controller: 200 OK<br/>{status: "provisioned", state: "pending"}
    else Unauthorized
        ControllerAPI-->>Controller: 401 Unauthorized
    end
```

## Revocation Impact Flow

```mermaid
sequenceDiagram
    participant Controller
    participant ControllerAPI
    participant DeviceRegistry
    participant IdentityEnforcement
    participant ConversationRegistry
    participant LoggingService
    
    Controller->>ControllerAPI: POST /api/device/revoke<br/>{device_id}<br/>X-Controller-Key: api-key
    ControllerAPI->>DeviceRegistry: revoke_device(device_id)
    DeviceRegistry-->>ControllerAPI: revoked: true
    
    ControllerAPI->>IdentityEnforcement: handle_revocation_impact(device_id)
    IdentityEnforcement->>ConversationRegistry: handle_participant_revocation(device_id)
    ConversationRegistry->>ConversationRegistry: remove_participant(conversation_id, device_id)
    ConversationRegistry-->>IdentityEnforcement: affected_conversations: [list]
    IdentityEnforcement-->>ControllerAPI: impact: {affected_conversations, conversations_closed}
    
    ControllerAPI->>LoggingService: log_audit_event(DEVICE_REVOKED)
    ControllerAPI-->>Controller: 200 OK<br/>{status: "revoked", affected_conversations: N}
```

## Error Handling

```mermaid
flowchart TD
    Start([Controller Request]) --> Auth{Valid API Key?}
    Auth -->|No| Unauthorized[401 Unauthorized]
    Auth -->|Yes| Validate{Valid Request?}
    Validate -->|No| BadRequest[400 Bad Request]
    Validate -->|Yes| CheckState{Device State Valid?}
    CheckState -->|No| Conflict[409 Conflict]
    CheckState -->|Yes| Process[Process Operation]
    Process --> Success[200 OK]
    Process -->|Device Not Found| NotFound[404 Not Found]
    Process -->|Backend Error| ServerError[500 Backend Failure]
    
    style Unauthorized fill:#ffcccc
    style BadRequest fill:#ffcccc
    style Conflict fill:#ffcccc
    style NotFound fill:#ffcccc
    style ServerError fill:#ffcccc
    style Success fill:#ccffcc
```

## References

- API Contracts (#10), Section 3.1 and 3.2
- Identity Provisioning (#11), Section 3 and 5
- State Machines (#7), Section 5
- Copy Rules (#13)
- Logging & Observability (#14)
