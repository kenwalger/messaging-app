# Abiqua Asset Management - Roadmap

This roadmap outlines the planned development phases for AAM. All implementations must follow frozen specifications (Assets #1-#18) and resolved TBDs/clarifications.

## Phase 1: Core Message Delivery ✅

**Status:** Completed

- [x] Message delivery service (client and backend)
- [x] Message lifecycle state machine implementation
- [x] Offline queuing and storage management
- [x] Message expiration enforcement
- [x] Duplicate detection
- [x] Retry logic with limits
- [x] Comprehensive unit tests (13 tests, all passing)
- [x] Type hints per PEP 484 (Project Best Practices #20)
- [x] Docstrings per PEP 257 (Project Best Practices #20)
- [x] Protocol interfaces for abstracted services
- [x] Project documentation (README, LICENSE, CONTRIBUTING, CHANGELOG, ROADMAP)

## Phase 1.5: Conversation Management ✅

**Status:** Completed

- [x] Conversation creation with explicit participant definition (Functional Spec #6, Section 4.1)
- [x] Conversation lifecycle state machine (State Machines #7, Section 4)
- [x] Participant addition and removal with group size enforcement (max 50)
- [x] Conversation closure handling (messages remain until expiration)
- [x] Participant revocation handling
- [x] Neutral enterprise mode support (read-only for revoked devices)
- [x] Backend conversation registry service
- [x] Integration with message delivery module
- [x] Comprehensive unit tests (18 tests, all passing)
- [x] Conversation lifecycle diagrams (Mermaid)

## Phase 2: Identity & Provisioning (Next)

**Status:** Planned

### Identity Management
- [ ] Device-bound identity implementation (Identity Provisioning #11)
- [ ] Identity provisioning lifecycle (State Machines #7, Section 2)
- [ ] Device authentication and session establishment (Functional Spec #6, Section 3.2)
- [ ] Device revocation and decommissioning (Lifecycle Playbooks #15, Sections 3-4)

### Controller Interface
- [ ] Controller authentication (token-based API key system per Resolved Clarifications)
- [ ] Device provisioning API (`/api/device/provision` per API Contracts #10)
- [ ] Device revocation API (`/api/device/revoke` per API Contracts #10)
- [ ] Provisioning confirmation endpoint (`/api/device/provision/confirm` per Resolved Clarifications)

### Security
- [ ] Cryptographic key generation and storage (platform secure keystores)
- [ ] Key rotation schedule (every 90 days or on revocation per Resolved TBDs)
- [ ] Secure storage service abstraction

## Phase 3: Encryption & Security

**Status:** Planned

### Encryption Service
- [ ] End-to-end encryption implementation
- [ ] Message payload encryption/decryption
- [ ] Key exchange and management
- [ ] Platform-specific secure storage integration

### Security Features
- [ ] Device loss/stolen handling (Threat Model #3, Section 4.2)
- [ ] Secure data deletion on revocation
- [ ] Clock skew handling (±2 minutes tolerance per Resolved Clarifications)
- [ ] Secure message storage at rest

## Phase 4: Network & Delivery

**Status:** Planned

### WebSocket Implementation
- [ ] WebSocket client with automatic reconnect (exponential backoff per Resolved Clarifications)
- [ ] WebSocket server for backend relay
- [ ] Session token management
- [ ] Delivery acknowledgment (ACK per message ID)

### REST Fallback
- [ ] REST polling client (30-second interval per Resolved TBDs)
- [ ] REST API endpoints implementation (API Contracts #10)
- [ ] Fallback mechanism (WebSocket → REST per Resolved TBDs)

### Network Handling
- [ ] Offline detection and queueing
- [ ] Network reconnection handling
- [ ] Message retry logic integration

## Phase 5: Conversation Management ✅

**Status:** Completed

### Conversation Lifecycle
- [x] Conversation creation (explicit, max 50 participants per Resolved TBDs)
- [x] Conversation state machine (State Machines #7, Section 4)
- [x] Participant management
- [x] Conversation closure handling

### Conversation Features
- [x] Conversation list management
- [x] Conversation metadata (Restricted classification per Data Classification #8)
- [x] Closed conversation handling (messages remain until expiration per Resolved Clarifications)

## Phase 6: UI/UX Implementation

**Status:** Planned

### User Interface
- [ ] Neutral enterprise-style UI (UX Behavior #12)
- [ ] Conversation list view
- [ ] Message composition and display
- [ ] Reverse chronological message order (newest first per Resolved Clarifications)
- [ ] Max 100 messages per conversation view (per Resolved TBDs)

### User Experience
- [ ] Neutral error messages (Copy Rules #13)
- [ ] Badge-only notifications (no banner, no sound per Resolved Clarifications)
- [ ] "Messaging Disabled" state for revoked devices
- [ ] Neutral enterprise mode (read-only for revoked devices per Resolved Clarifications)

### Platform Support
- [ ] iOS implementation
- [ ] Android implementation
- [ ] Web implementation

## Phase 7: Logging & Observability

**Status:** Planned

### Logging Service
- [ ] Content-free logging (Logging & Observability #14)
- [ ] Operational event logging (`/api/log/event` per API Contracts #10)
- [ ] Log retention (90 days per Resolved TBDs)
- [ ] Log purge automation

### Monitoring
- [ ] Metrics aggregation (1-hour windows per Resolved TBDs)
- [ ] Alert thresholds (≥5 failed messages per Resolved TBDs)
- [ ] Dashboard/audit interface
- [ ] System health monitoring

## Phase 8: Testing & Quality Assurance

**Status:** Ongoing

### Test Coverage
- [ ] Integration tests for complete message lifecycle
- [ ] Integration tests for identity provisioning
- [ ] Integration tests for device revocation
- [ ] End-to-end tests for critical flows
- [ ] Performance testing
- [ ] Security testing

### Quality Assurance
- [ ] Code coverage ≥80% for critical modules
- [ ] Linting and formatting automation
- [ ] CI/CD pipeline
- [ ] Automated test execution

## Phase 9: Documentation & Deployment

**Status:** Planned

### Documentation
- [ ] API documentation
- [ ] Deployment guides
- [ ] Operational runbooks
- [ ] Security documentation
- [ ] User guides

### Deployment
- [ ] Backend deployment (cloud-hosted per Resolved TBDs)
- [ ] Client app distribution
- [ ] Configuration management
- [ ] Monitoring and alerting setup

## Future Considerations

### Potential Enhancements (Subject to Spec Updates)
- Multi-platform support expansion
- Performance optimizations
- Scalability improvements (beyond 5000 concurrent devices per Resolved TBDs)
- Additional platform integrations

**Note:** All enhancements must be approved and added to frozen specifications before implementation. No features outside specifications will be implemented.

## Timeline

- **Phase 1**: ✅ Completed (including code quality standards)
- **Phase 1.5**: ✅ Completed (Conversation Management)
- **Phase 2**: Next (Identity & Provisioning)
- **Phase 3-9**: Planned (timeline TBD)

## Dependencies

- Phase 2 depends on Phase 1 (message delivery)
- Phase 3 depends on Phase 2 (identity management)
- Phase 4 depends on Phase 3 (encryption)
- Phase 5 depends on Phase 1 and Phase 2
- Phase 6 depends on Phases 1-5
- Phase 7 can proceed in parallel with other phases
- Phase 8 is ongoing throughout all phases
- Phase 9 depends on completion of Phases 1-7

## Notes

- All implementations must follow frozen specifications
- No features outside specifications will be added
- All TBDs must be resolved before implementation
- Breaking changes will be documented in CHANGELOG.md
