# Changelog

All notable changes to Abiqua Asset Management (AAM) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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
