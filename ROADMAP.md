# Abiqua Asset Management - Roadmap

This roadmap outlines the planned development phases for AAM. All implementations must follow frozen specifications (Assets #1-#18) and resolved TBDs/clarifications.

## Phase 1: Core Message Delivery ✅

**Status:** Completed

- [x] Message delivery service (client and backend)
- [x] Message lifecycle state machine implementation
- [x] Offline queuing and storage management
- [x] Message expiration enforcement
- [x] Duplicate detection (Message ID + content hash)
- [x] Retry logic with exponential backoff (max 5 attempts)
- [x] ACK handling per message ID with timeout (30s)
- [x] WebSocket reconnect with exponential backoff
- [x] REST polling fallback (every 30s when WebSocket unavailable)
- [x] Comprehensive unit tests (25 tests, all passing)
  - 12 tests for reliability hardening
  - 13 tests for core delivery
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

## Phase 2: Identity & Provisioning ✅

**Status:** Completed (Core Identity Management)

### Identity Management
- [x] Device-bound identity implementation (Identity Provisioning #11)
- [x] Identity provisioning lifecycle (State Machines #7, Section 5)
- [x] Device identity state model (Pending, Provisioned, Active, Revoked)
- [x] DeviceRegistry service with state tracking
- [x] Identity enforcement service (server-side only)
- [x] Device revocation handling (immediate and irreversible per Identity Provisioning #11, Section 5)
- [x] Key rotation scheduling (90 days or immediately upon revocation per Resolved TBDs)
- [x] Revocation impact handling (removes from conversations per State Machines #7, Section 4)
- [x] Neutral enterprise mode enforcement (revoked devices can read but cannot send/create/join per Resolved Clarifications #38)
- [x] Comprehensive unit tests (17 test cases, all passing)
- [x] Device identity lifecycle diagrams (Mermaid)

### Controller Interface
- [ ] Controller authentication (token-based API key system per Resolved Clarifications)
- [ ] Device provisioning API (`/api/device/provision` per API Contracts #10)
- [ ] Device revocation API (`/api/device/revoke` per API Contracts #10)
- [ ] Provisioning confirmation endpoint (`/api/device/provision/confirm` per Resolved Clarifications)

### Security
- [x] Key rotation schedule and triggers (every 90 days or on revocation per Resolved TBDs)
- [ ] Cryptographic key generation and storage (platform secure keystores)
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

## Phase 4: Network & Delivery ✅

**Status:** Completed

### WebSocket Implementation
- [x] WebSocket client with automatic reconnect (exponential backoff per Resolved Clarifications)
- [x] Session token management (X-Device-ID + ephemeral session token)
- [x] Delivery acknowledgment (ACK per message ID per Resolved Clarifications #51)
- [x] ACK timeout handling with retry

### REST Fallback
- [x] REST polling client (30-second interval per Resolved TBDs)
- [x] REST API endpoints implementation (API Contracts #10)
- [x] Fallback mechanism (WebSocket → REST per Resolved TBDs)
- [x] Automatic stop when WebSocket reconnects

### Network Handling
- [x] Offline detection and queueing
- [x] Network reconnection handling
- [x] Message retry logic with exponential backoff integration

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

### Backend Conversation API
- [x] POST `/api/conversation/create` - Create conversation endpoint (API Contracts #10)
- [x] POST `/api/conversation/join` - Join conversation endpoint
- [x] POST `/api/conversation/leave` - Leave conversation endpoint
- [x] POST `/api/conversation/close` - Close conversation endpoint
- [x] GET `/api/conversation/info` - Get conversation information endpoint
- [x] Permission enforcement (only provisioned devices per Identity Provisioning #11)
- [x] Group size limit enforcement (max 50 participants)
- [x] Conversation state validation
- [x] Neutral enterprise mode support (Resolved Clarifications #38)
- [x] Comprehensive unit tests (16 tests, all passing)
- [x] Conversation API lifecycle diagrams (Mermaid)

## Phase 5.5: API Boundary & Adapter Layer ✅

**Status:** Completed

### Client-Facing API Boundary
- [x] Client-facing API response schemas (DTOs) per API Contracts (#10)
- [x] API adapter layer mapping internal models to client DTOs
- [x] State mapping (internal states → client-visible states per UX Behavior #12, Section 4)
- [x] Error code enumeration and mapping (API Contracts #10, Section 6)
- [x] API versioning strategy (v1 per API Contracts #10)
- [x] Error normalization pipeline (neutral messages per Copy Rules #13, Section 4)
- [x] Content-free error responses (no internal details, stack traces, or sensitive info)
- [x] Comprehensive unit tests (15 test cases, all passing)
- [x] API boundary and adapter layer diagrams (Mermaid)

### Client-Safe DTOs
- [x] ClientMessageDTO (hides retry_count, internal states, payload)
- [x] ClientConversationDTO (hides participant IDs, shows count only)
- [x] ClientErrorResponse (neutral messages, no technical details)
- [x] ClientSuccessResponse (standardized success format with versioning)

## Phase 5.6: UI Domain Adapter Layer ✅

**Status:** Completed

### UI Domain Models
- [x] MessageViewModel with derived UX flags (is_expired, is_failed, is_read_only)
- [x] ConversationViewModel with derived UX flags (can_send, is_read_only, send_disabled)
- [x] ParticipantViewModel for participant display
- [x] DeviceStateViewModel with derived permission flags
- [x] Stateless view models (deterministically derived from API responses)

### UI Adapter Functions
- [x] UIAdapter mapping client API DTOs to UI domain models
- [x] Deterministic derivation of UX flags from API responses
- [x] Reverse chronological sorting (newest first per Resolved Clarifications #53)
- [x] Message filtering (expired, failed, active conversations)
- [x] Neutral enterprise mode support (read-only flags per Resolved Clarifications #38)
- [x] Comprehensive unit tests (13 test cases, all passing)
- [x] UI domain adapter layer diagrams (Mermaid)

## Phase 5.7: Read-Only UI Shell ✅

**Status:** Completed

### React Components
- [x] StatusIndicator component for device state display
- [x] ConversationList component for active conversations
- [x] MessageList component with reverse chronological ordering
- [x] MessageRow component with visual distinction for states
- [x] App component orchestrating the UI shell
- [x] TypeScript types mirroring Python UI domain models
- [x] Tailwind CSS styling with neutral, enterprise-safe visual tone
- [x] Mock data fixtures for Storybook-style testing
- [x] Unit tests for rendering, ordering, and neutral mode enforcement

### UI Features
- [x] Reverse chronological message order (newest first per Resolved Clarifications #53)
- [x] Read-only mode indicators (neutral enterprise mode per Resolved Clarifications #38)
- [x] Visual distinction for delivered/failed/expired messages per UX Behavior (#12)
- [x] Expired message filtering (removed automatically per UX Behavior #12, Section 3.4)
- [x] Failed message distinction (explicitly distinguishable per UX Behavior #12, Section 3.6)
- [x] No sound, no animation, no urgency cues per UX Behavior (#12), Section 2
- [x] Neutral color scheme (no red/green/security color metaphors per UX Behavior #12, Section 5)

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

## Phase 7: Logging & Observability ✅

**Status:** Completed

### Logging Service
- [x] Content-free logging (Logging & Observability #14)
- [x] Structured JSON logging with content validation
- [x] Operational event logging (all 7 permitted event types per Logging & Observability #14, Section 3)
- [x] Log retention (90 days per Resolved TBDs)
- [x] Log purge automation
- [x] Audit event recording (append-only, immutable per Data Classification #8)

### Monitoring
- [x] Metrics aggregation (1-hour windows per Resolved TBDs)
- [x] Alert thresholds (≥5 failed deliveries in 1-hour window per Resolved TBDs)
- [x] Metrics instrumentation (active devices, messages queued, failed deliveries, revoked devices)
- [x] Comprehensive unit tests (12 test cases, all passing)
- [x] Observability and audit enforcement diagrams (Mermaid)
- [ ] Dashboard/audit interface (UI implementation)
- [ ] System health monitoring (UI implementation)

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
- **Phase 1.5**: ✅ Completed (Conversation Management - Client)
- **Phase 2**: ✅ Completed (Identity & Provisioning - Core Identity Management)
- **Phase 4**: ✅ Completed (Network & Delivery)
- **Phase 5**: ✅ Completed (Conversation Management - Backend API)
- **Phase 5.5**: ✅ Completed (API Boundary & Adapter Layer)
- **Phase 5.6**: ✅ Completed (UI Domain Adapter Layer)
- **Phase 5.7**: ✅ Completed (Read-Only UI Shell)
- **Phase 7**: ✅ Completed (Logging & Observability - Core Services)
- **Phase 2.5**: Next (Controller API Endpoints for Provisioning/Revocation)
- **Phase 3, 6, 8-9**: Planned (timeline TBD)

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
