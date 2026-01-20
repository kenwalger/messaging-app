# Abiqua Asset Management (AAM)

**Version:** 0.1.0  
**Status:** Development

## Overview

Abiqua Asset Management (AAM) is a secure messaging system designed for organizations operating in high-risk, high-sensitivity environments. AAM provides secure communications with strict lifecycle controls, minimal metadata exposure, and a neutral enterprise-style user experience.

## Purpose

AAM addresses the need for secure communications that:
- Minimize data exposure
- Enforce strict lifecycle controls
- Reduce human error
- Avoid attracting undue attention during casual inspection

Unlike consumer or enterprise messaging platforms that prioritize usability and scale, AAM prioritizes operational control, predictability, and deterministic behavior.

## Target Users

**Primary Users:**
- Field operators
- Journalists in hostile regions
- NGO and humanitarian coordinators
- Internal red teams and security exercises

**Secondary Users:**
- Controllers / coordinators
- Security administrators
- Compliance auditors (metadata only)

## Key Features

- **One-to-one secure messaging** with end-to-end encryption
- **Small group messaging** (max 50 participants per conversation)
- **Message expiration** (default 7 days, configurable)
- **Device-bound identity** (no multi-device identity sharing)
- **Explicit provisioning and decommissioning** (controller-managed)
- **Remote access revocation** (immediate device disablement)
- **Offline queuing** (max 500 messages or 50MB per device)
- **Deterministic behavior** (all actions traceable to specifications)

## Architecture

AAM consists of:
- **Operator Devices**: Client applications (iOS, Android, Web) with device-bound identities
- **Backend Relay**: Stateless message relay (no plaintext storage)
- **Controller Interface**: Administrative interface for device provisioning and revocation
- **Secure Storage**: Platform-specific secure keystores for cryptographic material

## Security Model

AAM protects against:
- Unauthorized access to message content
- Accidental or opportunistic disclosure
- Data persistence beyond intended lifetimes
- Infrastructure compromise without content exposure
- Device loss or theft
- Insider misuse within defined trust boundaries

**Note:** AAM is not designed to defend against nation-state APTs, physical coercion, platform owner hostility, or endpoint compromise. See Threat Model Specification (#3) for details.

## Project Status

**Current Phase:** Backend conversation API implementation

**Completed:**
- Message delivery service (client and backend)
- Message lifecycle state machine
- Offline queuing and storage management
- Message expiration enforcement
- Duplicate detection (Message ID + content hash)
- Retry logic with exponential backoff (max 5 attempts)
- ACK handling per message ID with timeout (30s)
- WebSocket reconnect with exponential backoff
- REST polling fallback (every 30s when WebSocket unavailable)
- Conversation management service (client and backend)
- Backend conversation API service with REST endpoints
  - Create, join, leave, and close conversation endpoints
  - Permission enforcement (only provisioned devices)
  - Group size limit enforcement (max 50 participants)
  - Neutral enterprise mode support
- Conversation lifecycle state machine (Uncreated → Active → Closed)
- Participant management with group size enforcement (max 50)
- Conversation closure handling
- Neutral enterprise mode support (read-only for revoked devices)
- Comprehensive unit tests (59 tests total, all passing)
  - 16 tests for backend conversation API
  - 12 tests for message delivery reliability hardening
  - 18 tests for conversation management
  - 13 tests for message delivery
- Full type hints per PEP 484 (Project Best Practices #20)
- Complete docstrings per PEP 257 (Project Best Practices #20)
- Protocol interfaces for service abstractions

**In Progress:**
- Identity provisioning and lifecycle management
- Encryption service integration
- WebSocket and REST client implementations
- UI/UX implementation

## Getting Started

### Prerequisites

- Python 3.8+
- Virtual environment (recommended)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd AbiquaAssetManagement

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_message_delivery.py
pytest tests/test_message_delivery_hardening.py
pytest tests/test_conversation_manager.py
pytest tests/test_conversation_api.py

# Run all tests
pytest
```

## Project Structure

```
AbiquaAssetManagement/
├── specs/              # Frozen specifications (Assets #1-#18)
├── src/
│   ├── client/         # Operator device app code
│   ├── backend/        # Backend relay and controller interfaces
│   └── shared/         # Shared utilities, types, constants
├── tests/              # Unit and integration tests
├── docs/               # Additional documentation
├── scripts/            # Build, deployment, and CI scripts
└── README.md           # This file
```

## Documentation

- **Specifications**: See `specs/` directory for complete project specifications
- **API Documentation**: See `docs/` directory for API documentation and diagrams
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Changelog**: See [CHANGELOG.md](CHANGELOG.md)
- **Roadmap**: See [ROADMAP.md](ROADMAP.md)

## Legal & Ethical Constraints

AAM is designed for legitimate organizational use only. The system must not be used for:
- Criminal activity facilitation
- Organized crime coordination
- Terrorist activity
- Human trafficking
- Drug trafficking
- Financial fraud
- Sanctions evasion
- Covert surveillance of individuals
- Deployment without device owner consent

See Legal & Ethical Constraints Specification (#4) for complete details.

## License

See [LICENSE.md](LICENSE.md) for license information.

## References

All implementation follows frozen specifications:
- PRD (#1)
- Non-Goals & Prohibited Behaviors (#2)
- Threat Model (#3)
- Legal & Ethical Constraints (#4)
- Do Not Invent List (#5)
- Functional Specification (#6)
- State Machines (#7)
- Data Classification & Retention (#8)
- Architecture Diagram (#9)
- API Contracts (#10)
- Identity Provisioning (#11)
- UX Behavior (#12)
- Copy Rules (#13)
- Logging & Observability (#14)
- Lifecycle Playbooks (#15)
- ADRs (#16)
- Repo & Coding Standards (#17)
- Cursor Master Prompt (#18)
- Project Best Practices (#20)

## Contact

For questions or issues, please see [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.
