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

**Status:** Completed (Core Identity Management + Controller API)

### Identity Management
- [x] Device-bound identity implementation (Identity Provisioning #11)
- [x] Identity provisioning lifecycle (State Machines #7, Section 5)
- [x] Device identity state model (Pending, Provisioned, Active, Revoked)
- [x] DeviceRegistry service with state tracking
- [x] Identity enforcement service (server-side only)

### Controller API Endpoints
- [x] POST /api/device/provision: Creates device in Pending state per API Contracts (#10), Section 3.1
- [x] POST /api/device/provision/confirm: Transitions Pending → Provisioned per Identity Provisioning (#11), Section 3
- [x] POST /api/device/revoke: Revokes device immediately and irreversibly per API Contracts (#10), Section 3.2
- [x] Controller authentication via API key (X-Controller-Key header) per API Contracts (#10), Section 5
- [x] Controller DTOs and response types (ProvisionDeviceRequest/Response, ConfirmProvisioningRequest/Response, RevokeDeviceRequest/Response)
- [x] Comprehensive unit tests (19 test cases) covering:
  - Valid state transitions
  - Invalid state transitions
  - Authorization failures
  - Idempotent revoke handling
  - Revocation impact on conversations
- [x] Controller API documentation with Mermaid diagrams
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

## Phase 5.8: Interactive Messaging (Send Path Only) ✅

**Status:** Completed

### Message Composition and Sending
- [x] MessageComposer component for message composition
- [x] SendButton component with disabled states
- [x] MessageApiService interface for client-side message sending
- [x] Optimistic updates (message enters PENDING state immediately per deterministic rules)
- [x] Delivery state transitions (PENDING → DELIVERED, PENDING → FAILED)
- [x] Visual indicators for pending (queued), delivered, and failed messages
- [x] State handling for pending messages and delivery updates
- [x] API integration using existing adapters
- [x] Comprehensive unit tests for send path components

### Send Disabled Conditions
- [x] Sending disabled when neutral enterprise mode is active
- [x] Sending disabled when device is revoked
- [x] Sending disabled when conversation is closed
- [x] Visual feedback for disabled states

### Constraints Enforced
- [x] No attachments
- [x] No message editing
- [x] No retry UI
- [x] No notifications
- [x] No animations beyond basic transitions
- [x] No content logged or leaked

## Phase 5.9: Incoming Message Handling & Live Updates ✅

**Status:** Completed

### Transport Abstraction
- [x] MessageTransport interface (WebSocket + REST polling)
- [x] WebSocket transport implementation (preferred)
- [x] REST polling transport implementation (fallback, 30-second interval)
- [x] Transport factory for creating appropriate transport
- [x] UI does not care which transport is active

### Authentication
- [x] Uses existing device authentication mechanism (X-Device-ID header)
- [x] No new auth flows invented
- [x] Per API Contracts (#10), Section 5

### Incoming Message Handling
- [x] Message normalization into MessageViewModel
- [x] Deduplication by message ID (primary check)
- [x] Preserves ordering guarantees (reverse chronological)
- [x] State reconciliation (merge without overwriting incorrectly)

### State Reconciliation
- [x] Merge incoming messages without reordering sent messages
- [x] Prevents duplicate messages
- [x] Prevents overwriting delivery state incorrectly
- [x] State progression: sent → delivered/failed (one-way)

### UI Updates
- [x] New messages appear automatically without page reload
- [x] Existing message lists update efficiently
- [x] Message state transitions remain visible and accurate
- [x] Expired messages removed automatically

### Connection Lifecycle
- [x] Handle connect/disconnect/reconnect
- [x] On reconnect, reconcile missed messages using REST
- [x] Connection status tracked internally (no UI indicator yet)
- [x] Automatic reconnection with exponential backoff (WebSocket)

### Testing
- [x] Unit tests for message deduplication
- [x] Unit tests for state reconciliation
- [x] Unit tests for reconnection reconciliation
- [x] Unit tests for ordering guarantees

## Phase 6: Backend Server Infrastructure ✅

**Status:** Completed

### Backend Server
- [x] FastAPI server entrypoint with explicit dependency injection
- [x] All API endpoints wired to existing services (no business logic changes)
- [x] Controller API endpoints: `/api/device/provision`, `/api/device/provision/confirm`, `/api/device/revoke`
- [x] Conversation API endpoints: `/api/conversation/create`, `/api/conversation/join`, `/api/conversation/leave`, `/api/conversation/close`, `/api/conversation/info`
- [x] Message API endpoints: `/api/message/send`, `/api/message/receive`
- [x] Logging API endpoint: `/api/log/event`
- [x] WebSocket endpoint: `/ws/messages` for real-time message delivery
- [x] Health check endpoint: `/health`
- [x] Device authentication via `X-Device-ID` header
- [x] Controller authentication via `X-Controller-Key` header
- [x] WebSocket connection manager (`FastAPIWebSocketManager`) implementing `WebSocketManager` Protocol
- [x] Server runs on `http://0.0.0.0:8000` by default for local development
- [x] Clear TODOs for encryption and auth hardening (TLS, rate limiting, etc.)

### Infrastructure
- [x] FastAPI and uvicorn dependencies added to `requirements.txt`
- [x] Explicit service initialization with dependency injection
- [x] Infrastructure-only work (no business logic changes)

## Phase 6.1: Frontend Development Server ✅

**Status:** Completed

### Frontend Dev Server
- [x] Vite build tool setup with React and TypeScript
- [x] API base URL configuration via `VITE_API_BASE_URL` environment variable
- [x] Development server with hot reload (runs on `http://localhost:5173`)
- [x] TypeScript strict mode enabled
- [x] Tailwind CSS configured and integrated
- [x] HTTP message API service implementation (`HttpMessageApiService`)
- [x] WebSocket URL automatically derived from API base URL
- [x] Entry point files created (`index.html`, `src/main.tsx`, `src/index.css`, `src/env.d.ts`)
- [x] Configuration files created (`vite.config.ts`, `tsconfig.json`, `tailwind.config.js`, `postcss.config.js`)
- [x] `package.json` with all required dependencies
- [x] Node.js >= 18.0.0 requirement documented
- [x] Mock fallback still supported for testing (via `MockMessageApiService`)

## Phase 6.1.1: Frontend-Backend Integration ✅

**Status:** Completed

### Integration Services
- [x] Health check service for backend connectivity verification
- [x] Device API service for fetching device state from backend
- [x] Conversation API service for fetching conversation information
- [x] Message fetch API service for fetching initial messages with pagination

### Data Flow
- [x] Health check on app startup (development logging only)
- [x] Device state fetched and derived from backend API responses
- [x] Messages fetched via `GET /api/message/receive` endpoint
- [x] Conversations derived from messages and conversation info endpoints
- [x] Reverse chronological ordering for conversations and messages (newest first)
- [x] Read-only flags set based on device state
- [x] WebSocket connection established automatically for real-time updates
- [x] Graceful fallback to mock data if backend unavailable

### Error Handling
- [x] All errors normalized via existing adapter logic
- [x] Neutral error messages (no stack traces or backend details exposed)
- [x] Silent error handling with automatic retries
- [x] Network errors handled gracefully

### Documentation
- [x] README.md updated with frontend-backend integration section
- [x] Required backend headers documented (`X-Device-ID`, `X-Controller-Key`)
- [x] Controller setup documented (`CONTROLLER_API_KEYS` environment variable)
- [x] Expected local dev flow documented (2 terminals)

## Phase 6.1.2: WebSocket Resilience & REST Fallback ✅

**Status:** Completed

### Composite Transport
- [x] Composite transport implementation (`src/ui/services/compositeTransport.ts`) managing both WebSocket and REST polling
- [x] Automatic REST polling fallback after 15s WebSocket disconnect (per Resolved Clarifications #51)
- [x] REST polling stops immediately when WebSocket reconnects (WebSocket is preferred)
- [x] Transport factory updated to use composite transport when both WebSocket and API URLs available

### Resilience Features
- [x] WebSocket reconnect with exponential backoff (1s, 2s, 4s, 8s, ... up to 60s max)
- [x] Automatic fallback to REST polling when WebSocket unavailable >15s
- [x] Seamless transport switching (UI does not care which transport is active)
- [x] Message deduplication verified (handled by message store, prevents duplicates when switching transports)

### Observability
- [x] Development-only logging for reconnect attempts (no content exposed)
- [x] Development-only logging for REST fallback activation/deactivation
- [x] Logging follows Logging & Observability (#14) - event types only, no content

### Testing
- [x] Unit tests for composite transport resilience behavior
- [x] Tests verify WebSocket as primary transport
- [x] Tests verify REST fallback after 15s disconnect
- [x] Tests verify REST polling stops on WebSocket reconnect

### Documentation
- [x] README.md updated with WebSocket Resilience section
- [x] Documented reconnect behavior, REST fallback conditions, and transport switching
- [x] CHANGELOG.md updated with resilience improvements

## Phase 6.1.3: End-to-End Message Delivery Flow ✅

**Status:** Completed

### Message Delivery Flow
- [x] Frontend ACK sending when receiving messages via WebSocket
- [x] Backend ACK forwarding to sender when recipient acknowledges
- [x] Frontend ACK handling to update message state (PENDING → DELIVERED)
- [x] Complete message lifecycle: Send → Delivery → ACK → UI Update
- [x] Message state transitions: PENDING → DELIVERED → ACTIVE
- [x] Automatic UI updates without refresh (optimistic updates + ACK reconciliation)
- [x] WebSocket-based real-time message delivery and ACK handling
- [x] REST polling fallback for message delivery (when WebSocket unavailable)
- [x] Message ordering maintained (reverse chronological, newest first)

### Testing
- [x] End-to-end flow verified: Two browser windows can send/receive messages
- [x] ACK lifecycle verified: Messages transition from PENDING to DELIVERED
- [x] UI state updates verified: Messages appear immediately, state updates automatically
- [x] Message ordering verified: Newest messages appear first

### Bug Fixes
- [x] Fixed critical ACK detection bug: ACK detection now correctly identifies ACKs regardless of conversation_id presence
- [x] **CRITICAL**: Added missing `get_message_sender()` and `get_message_conversation()` methods to `MessageRelayService`
  - Methods were referenced in `server.py` but did not exist on disk, causing `AttributeError` at runtime
  - Methods now properly implemented, preventing runtime errors in ACK forwarding
  - Replaced private attribute access with proper public API methods
- [x] Removed duplicate UI notifications in ACK handling path
- [x] Improved race condition handling in multi-recipient ACK scenarios
- [x] Enhanced conversation_id handling in ACK forwarding

### Developer-Facing UX Instrumentation
- [x] Message state visibility: PENDING (italic + 🕐), DELIVERED (normal), FAILED (muted + ⚠)
- [x] Connection status indicator: WebSocket connected/reconnecting, REST polling fallback
- [x] Debug mode toggle: Show message metadata (ID, state, timestamps) for manual testing
- [x] UX guardrails: Disable send when connection initializing/disconnected, prevent duplicate sends
- [x] Connection status tracking: Expose connection status from MessageHandlerService to UI

### Documentation
- [x] README.md updated with end-to-end flow documentation
- [x] README.md updated with Manual Testing Checklist section
- [x] Testing instructions for two-browser-window scenario
- [x] Known limitations documented (POC status)
- [x] CHANGELOG.md updated with delivery flow completion and bug fixes

## Phase 6.1.5: Local Development Connectivity ✅

**Status:** Completed

### CORS Configuration
- [x] CORS middleware added to FastAPI backend for local development
- [x] Environment-aware CORS (permissive in dev, strict in production)
- [x] Allowed origins: `http://localhost:5173`, `http://127.0.0.1:5173`
- [x] Allowed methods: `GET`, `POST`, `OPTIONS` (CORS preflight support)
- [x] Allowed headers: `Content-Type`, `Authorization`, `X-Device-ID`, `X-Controller-Key`
- [x] Credentials: `false` (not required for local development)
- [x] Health endpoint includes CORS headers automatically
- [x] REST polling endpoint (`/api/message/receive`) passes CORS preflight

### WebSocket Configuration
- [x] WebSocket endpoint (`/ws/messages`) accepts connections from browser origins
- [x] Device authentication via `device_id` query parameter (per existing spec)
- [x] WebSocket security preserved (device validation, active state check)
- [x] No CORS bypass - WebSocket protocol handles origin validation

### Documentation
- [x] README.md updated with CORS configuration details
- [x] Environment variable documentation (`ENVIRONMENT` for production mode)
- [x] Local development flow updated with CORS information

## Phase 6.1.6: Implement /api/message/send Endpoint ✅

**Status:** Completed

### Endpoint Implementation
- [x] POST `/api/message/send` endpoint per API Contracts (#10), Section 3.3
- [x] Request payload validation:
  - Required fields: `message_id` (UUID v4), `conversation_id`, `payload`, `timestamp` (ISO 8601)
  - Optional field: `expiration` (ISO 8601, defaults to timestamp + 7 days)
  - Payload encoding validation (base64 or hex)
  - Payload size validation (≤ 50KB per MAX_MESSAGE_PAYLOAD_SIZE_KB)
- [x] Timestamp validation:
  - Rejects expired timestamps (with CLOCK_SKEW_TOLERANCE_MINUTES tolerance)
  - Validates ISO 8601 format
- [x] Conversation validation:
  - Checks conversation existence (returns 404 if not found)
  - Checks conversation state (returns 400 if not ACTIVE)
  - Derives recipients from conversation participants (excluding sender)
- [x] Message relay integration:
  - Calls `MessageRelayService.relay_message()` to register message in delivery state machine
  - Message enters PendingDelivery state
  - Forwards to WebSocket recipients or offline queue
  - ACK timer started (30s timeout)
- [x] Response handling:
  - Returns 202 Accepted on success with `{"status": "accepted", "message_id": "<uuid>"}`
  - Returns 400 Bad Request for validation errors
  - Returns 404 Not Found for non-existent conversations
  - Returns 500 Internal Server Error for delivery failures
- [x] Logging and observability:
  - Logs message send attempts (metadata only, no content) using LogEventType.MESSAGE_ATTEMPTED
  - Logs delivery failures using LogEventType.DELIVERY_FAILED
  - Uses `message_size_bytes` field (not `payload_size_bytes`) to comply with logging service validation
  - All logging per Logging & Observability (#14), Section 4

### Testing
- [x] Comprehensive unit tests (13 test cases) in `tests/test_message_send_endpoint.py`:
  - Successful message send (202 Accepted)
  - Missing required fields (400 Bad Request)
  - Invalid message_id format (400 Bad Request)
  - Expired timestamp (400 Bad Request)
  - Empty payload (400 Bad Request)
  - Payload too large (400 Bad Request)
  - Conversation not found (404 Not Found)
  - Conversation not active (400 Bad Request)
  - Expiration derivation (defaults to timestamp + 7 days)
  - Logging metadata verification (no content logged)
  - All validation error cases covered

### Dependencies
- [x] Added `httpx>=0.24.0,<1.0.0` to `requirements.txt` (required for FastAPI TestClient)

### Code Quality
- [x] Fixed logging field name (`payload_size_bytes` → `message_size_bytes`) to comply with prohibited key validation
- [x] Fixed conversation validation order (existence check before state check) for proper status codes
- [x] Fixed logging service enum usage (LogEventType enum instead of string constants)

## Phase 6.2: UI/UX Implementation

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
- **Phase 5.8**: ✅ Completed (Interactive Messaging - Send Path Only)
- **Phase 5.9**: ✅ Completed (Incoming Message Handling & Live Updates)
- **Phase 6**: ✅ Completed (Backend Server Infrastructure)
- **Phase 6.1**: ✅ Completed (Frontend Development Server)
- **Phase 6.1.1**: ✅ Completed (Frontend-Backend Integration)
- **Phase 6.1.2**: ✅ Completed (WebSocket Resilience & REST Fallback)
- **Phase 6.1.3**: ✅ Completed (End-to-End Message Delivery Flow)
- **Phase 6.1.4**: ✅ Completed (Developer-Facing UX Instrumentation)
- **Phase 6.1.5**: ✅ Completed (Local Development Connectivity - CORS & WebSocket)
- **Phase 6.1.6**: ✅ Completed (Implement /api/message/send Endpoint)
- **Phase 7**: ✅ Completed (Logging & Observability - Core Services)
- **Phase 2.5**: ✅ Completed (Controller API Endpoints for Provisioning/Revocation)
- **Phase 6.2**: Next (UI/UX Implementation)
- **Phase 3, 8-9**: Planned (timeline TBD)

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
