# Changelog

All notable changes to Abiqua Asset Management (AAM) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Incoming message handling and live updates
  - Transport abstraction layer (WebSocket + REST polling)
  - WebSocket transport implementation with automatic reconnection
  - REST polling transport fallback (30-second interval)
  - Message store with deduplication and ordering
  - Message handler service coordinating transport and store
  - State reconciliation (merge without overwriting incorrectly)
  - Automatic UI updates when new messages arrive
  - Connection lifecycle handling (connect/disconnect/reconnect)
  - Reconnection reconciliation (missed messages fetched on reconnect)
  - Comprehensive unit tests for deduplication and reconnection
  - Transport factory for creating appropriate transport
  - No content logged or leaked per deterministic rules
  - Messages appear automatically without page reload
  - Preserves reverse chronological ordering
  - Handles expired message cleanup automatically

### Fixed
- PR review feedback fixes for interactive messaging
  - Removed console.error logging in MessageComposer (violates "no content logged or leaked" rule)
  - Removed unused handleDeliveryUpdate callback in App.tsx (delivery updates handled via subscription)
  - Simplified delivery state transition handling
  - Updated README.md with local development instructions (backend and frontend)

### Added
- Interactive messaging (send path only)
  - MessageComposer component for message composition and sending
  - SendButton component with disabled states and sending indicator
  - MessageApiService interface for client-side message sending
  - Optimistic updates (message enters PENDING state immediately)
  - Delivery state transitions (PENDING → DELIVERED, PENDING → FAILED)
  - Visual indicators for pending (queued), delivered, and failed messages
  - State handling for pending messages and delivery updates
  - API integration using existing adapters
  - Comprehensive unit tests for send path components
  - Sending disabled when: neutral enterprise mode, revoked device, or closed conversation
  - No retry controls exposed in UI per constraints
  - No content logged or leaked per deterministic rules
- Read-only UI shell (React + TypeScript + Tailwind CSS)
  - React components for read-only message and conversation display
  - StatusIndicator component for device state display
  - ConversationList component for active conversations
  - MessageList component with reverse chronological ordering
  - MessageRow component with visual distinction for states
  - App component orchestrating the UI shell
  - TypeScript types mirroring Python UI domain models
  - Tailwind CSS styling with neutral, enterprise-safe visual tone
  - Mock data fixtures for Storybook-style testing
  - Unit tests for rendering, ordering, and neutral mode enforcement
  - No sound, no animation, no urgency cues per UX Behavior (#12)
  - Visual distinction for delivered/failed/expired messages
  - Read-only mode indicators for neutral enterprise mode
- UI domain adapter layer
  - UI domain models (view models) per UX Behavior (#12)
  - MessageViewModel with derived UX flags (is_expired, is_failed, is_read_only)
  - ConversationViewModel with derived UX flags (can_send, is_read_only, send_disabled)
  - ParticipantViewModel for participant display
  - DeviceStateViewModel with derived permission flags
  - UIAdapter mapping client API DTOs to UI domain models
  - Deterministic derivation of UX flags from API responses
  - Reverse chronological sorting (newest first per Resolved Clarifications #53)
  - Message filtering (expired, failed, active conversations)
  - Neutral enterprise mode support (read-only flags per Resolved Clarifications #38)
  - Comprehensive unit tests (14 test cases, all passing)
  - UI domain adapter layer diagrams (Mermaid)
- Client-facing API boundary and adapter layer
  - Client-facing API response schemas (DTOs) per API Contracts (#10)
  - API adapter layer mapping internal models to client DTOs (UX Behavior #12, Section 3.6)
  - Error code enumeration and mapping (API Contracts #10, Section 6)
  - API versioning strategy (v1 per API Contracts #10)
  - State mapping (internal states → client-visible states per UX Behavior #12, Section 4)
  - Error normalization pipeline (neutral messages per Copy Rules #13, Section 4)
  - Content-free error responses (no internal details, stack traces, or sensitive info)
  - Comprehensive unit tests (15 test cases, all passing)
  - API boundary and adapter layer diagrams (Mermaid)
- Logging, observability, and audit enforcement
  - Structured logging utilities with JSON format (Logging & Observability #14, Section 2)
  - Content-free logging validation (no message content, keys, or sensitive data per Logging & Observability #14, Section 4)
  - LoggingService with log retention and purge enforcement (90 days per Resolved TBDs)
  - Audit event model and recorder (append-only, immutable per Data Classification #8, Section 3)
  - MetricsService with 1-hour aggregation windows (Resolved TBDs)
  - Alert threshold logic (≥5 failed deliveries in 1-hour window per Resolved TBDs)
  - Metrics instrumentation for: active devices, messages queued, failed deliveries, revoked devices
  - Comprehensive unit tests (12 test cases, all passing)
  - Observability and audit enforcement diagrams (Mermaid)
- Device identity and revocation enforcement
  - Device identity state model (Pending, Provisioned, Active, Revoked per State Machines #7, Section 5)
  - DeviceRegistry service with identity state tracking (Identity Provisioning #11)
  - Identity enforcement service with server-side permission checks (Functional Spec #6, Section 3.2)
  - Revocation handling logic (immediate and irreversible per Identity Provisioning #11, Section 5)
  - Key rotation trigger handling (every 90 days or immediately upon revocation per Resolved TBDs)
  - Server-side enforcement for message sending, conversation creation/join (Resolved Clarifications #38)
  - Neutral enterprise mode support (revoked devices can read but cannot send/create/join)
  - Revocation impact handling (removes device from all conversations per State Machines #7, Section 4)
  - Comprehensive unit tests (17 test cases, all passing)
  - Device identity lifecycle diagrams (Mermaid)
- Backend conversation API service
  - POST `/api/conversation/create` - Create conversation with permission enforcement (Functional Spec #6, Section 4.1)
  - POST `/api/conversation/join` - Join conversation with group size validation (max 50 per Resolved TBDs)
  - POST `/api/conversation/leave` - Leave conversation (closes if last participant per State Machines #7, Section 4)
  - POST `/api/conversation/close` - Close conversation (participants only)
  - GET `/api/conversation/info` - Get conversation information (supports neutral enterprise mode per Resolved Clarifications #38)
  - Permission enforcement (only provisioned devices may create/join per Identity Provisioning #11)
  - Group size limit enforcement (max 50 participants, checked before join)
  - Conversation state validation (cannot join closed conversations)
  - Neutral enterprise mode support (revoked devices can view but cannot create/join)
  - Comprehensive unit tests (16 test cases, all passing)
  - Conversation API lifecycle diagrams (Mermaid)
- Core message delivery module implementation
  - Message creation, encryption, and delivery (Functional Spec #6, Sections 4.2-4.5)
  - Message lifecycle state machine (State Machines #7, Section 3)
  - Offline queuing with storage limits (max 500 messages/50MB per Resolved TBDs)
  - Message expiration enforcement (default 7 days, device-local timers)
  - Duplicate detection (Message ID + content hash per Resolved Clarifications)
  - Retry logic with limits (max 5 attempts per Resolved TBDs)
  - WebSocket and REST delivery mechanisms (Resolved TBDs)
- Conversation management module implementation
  - Conversation creation with explicit participant definition (Functional Spec #6, Section 4.1)
  - Conversation lifecycle state machine (Uncreated → Active → Closed per State Machines #7, Section 4)
  - Participant addition and removal with group size enforcement (max 50 per Resolved TBDs)
  - Conversation closure handling (all messages remain until expiration per Resolved Clarifications)
  - Participant revocation handling (removes from all conversations, closes if all revoked)
  - Neutral enterprise mode support (read-only for revoked devices per Resolved Clarifications)
  - Active conversation retrieval sorted by last message timestamp (UX Behavior #12)
  - Integration with message delivery module (conversation state checks)
- Backend conversation registry service
  - Conversation membership tracking (Restricted classification per Data Classification #8)
  - Participant management and revocation handling
  - Conversation closure and cleanup
- Backend message relay service
  - Encrypted message relay (no plaintext storage per Functional Spec #6, Section 5.1)
  - WebSocket and REST delivery support
  - Expiration enforcement
  - Metadata handling (Restricted classification per Data Classification #8)
- Shared types and constants
  - Message data structures and state enums
  - Conversation data structures and state enums
  - Constants from resolved TBDs and clarifications
  - UTC time helper function (timezone-aware)
- Message delivery reliability hardening
  - ACK handling per message ID with timeout (30s per Resolved Clarifications #51)
  - Exponential backoff retry policy (base * 2^retry_count, max 60s per Lifecycle Playbooks #15)
  - WebSocket reconnect with exponential backoff (Resolved Clarifications #51)
  - REST polling fallback (every 30s when WebSocket unavailable per Resolved TBDs #18)
  - Enhanced retry logic with exponential backoff for offline queue processing
  - Expired message rejection enforcement (Functional Spec #6, Section 4.4)
  - Duplicate message suppression (Message ID + content hash per Resolved Clarifications #35)
- Comprehensive unit tests
  - 13 test cases for UI domain adapter layer (all passing)
  - 15 test cases for API adapter layer (all passing)
  - 12 test cases for logging, observability, and audit enforcement (all passing)
  - 18 test cases for device identity and revocation enforcement (all passing)
  - 16 test cases for backend conversation API (all passing)
  - 12 test cases for message delivery reliability hardening (all passing)
  - 18 test cases for conversation management (all passing)
  - 13 test cases for message delivery (all passing)
  - Test coverage for critical paths
  - Timer cleanup in test teardown to prevent pytest hanging
- Project infrastructure
  - pytest.ini configuration
  - setup.py for development installation
  - .gitignore with Python and project-specific ignores
  - requirements.txt with dependencies
  - Package structure with __init__.py files
- Documentation
  - UI domain adapter layer diagrams (Mermaid)
  - API boundary and adapter layer diagrams (Mermaid)
  - Observability and audit enforcement diagrams (Mermaid)
  - Device identity lifecycle diagrams (Mermaid)
  - Conversation API lifecycle diagrams (Mermaid)
  - Message lifecycle diagrams (Mermaid)
  - Conversation lifecycle diagrams (Mermaid)
  - Message delivery reliability diagrams (Mermaid)
    - Delivery lifecycle with ACK
    - Retry & failure state transitions
    - WebSocket reconnect & REST fallback flow
    - Exponential backoff retry flow
    - REST polling message processing
    - ACK timeout handling
  - Client module README
  - Top-level documentation files (README.md, LICENSE.md, CONTRIBUTING.md, CHANGELOG.md, ROADMAP.md)

### Changed
- **Code Quality Improvements** (Project Best Practices #20)
  - Added comprehensive type hints per PEP 484 to all functions and classes
  - Added complete docstrings per PEP 257 with Args, Returns, and Raises sections
  - Created Protocol interfaces for abstracted services (EncryptionService, StorageService, WebSocketClient, HttpClient, LogService, DeviceRegistry, WebSocketManager)
  - All public methods, arguments, and return types fully annotated
  - Enhanced docstrings explaining behavior, arguments, return values, and exceptions

### Fixed
- Timer threads now properly cleaned up in test teardown to prevent pytest hanging
- Conversation participant addition now returns False (instead of raising ValueError) for closed conversations
- Timer threads set as daemon threads to allow clean process exit
- HttpClient Protocol missing get() method definition (added to match REST polling usage)
- DeviceRegistry missing provision_device() method for Pending → Provisioned transition (added to complete API surface)

### Technical Improvements
- Use timezone-aware datetime (utc_now() helper) to resolve deprecation warnings
- All code follows Repo & Coding Standards (#17) and Project Best Practices (#20)
- Comprehensive inline documentation with spec references
- Full type safety with Protocol-based interfaces
- No linting errors
- Proper thread cleanup in tests
- Deterministic message delivery with ACK tracking and exponential backoff
- Robust WebSocket/REST fallback mechanism with automatic reconnection

## [0.1.0] - 2024-XX-XX

### Added
- Initial project structure
- Frozen specifications (Assets #1-#18)
- Resolved TBDs and clarifications (27 TBDs + 6 clarifications)
- Core message delivery module
- Project documentation

---

## Version History

- **0.1.0**: Initial release with core message delivery module

## Notes

- All changes must reference relevant specification IDs
- Breaking changes will be clearly marked
- Security-related changes will be highlighted
- All implementations follow frozen specifications (Assets #1-#18)
