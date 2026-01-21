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

**Current Phase:** Interactive messaging (send path only)

**Completed:**
- Interactive messaging (send path only)
  - Message composition and sending
  - Optimistic updates and delivery state transitions
  - Visual indicators for pending/delivered/failed states
  - Disabled send conditions (neutral enterprise mode, revoked device, closed conversation)
- Read-only UI shell (React + TypeScript + Tailwind CSS)
- Read-only UI shell (React + TypeScript + Tailwind CSS)
  - React components for read-only display
  - Tailwind CSS styling (neutral, enterprise-safe)
  - TypeScript types for UI domain models
  - Mock data fixtures
  - Unit tests for components
- UI domain adapter layer
- UI domain adapter layer
  - UI domain models (view models) for presentation
  - Derived UX flags (canSend, isReadOnly, isExpired, isFailed)
  - Reverse chronological sorting (newest first)
  - Message and conversation filtering
  - Neutral enterprise mode support
- Client-facing API boundary and adapter layer
- Client-facing API boundary and adapter layer
  - Client-safe DTOs (hide internal implementation details)
  - State mapping (internal → client-visible states)
  - Error normalization (neutral messages only)
  - API versioning (v1)
  - Content-free error responses
- Logging, observability, and audit enforcement
  - Structured JSON logging (content-free)
  - Log retention and purge enforcement (90 days)
  - Metrics aggregation (1-hour windows)
  - Alert threshold logic (≥5 failed deliveries)
  - Audit event recording (append-only, immutable)
- Device identity and revocation enforcement
  - Device identity state model (Pending, Provisioned, Active, Revoked)
  - DeviceRegistry service with identity tracking
  - Identity enforcement service (server-side only)
  - Revocation handling (immediate and irreversible)
  - Key rotation scheduling (90 days or on revocation)
  - Neutral enterprise mode support
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
- Comprehensive unit tests (118 tests total, all passing)
  - 14 tests for UI domain adapter layer
  - 15 tests for API adapter layer
  - 12 tests for logging, observability, and audit enforcement
  - 18 tests for device identity and revocation enforcement
  - 16 tests for backend conversation API
  - 12 tests for message delivery reliability hardening
  - 18 tests for conversation management
  - 13 tests for message delivery
- Full type hints per PEP 484 (Project Best Practices #20)
- Complete docstrings per PEP 257 (Project Best Practices #20)
- Protocol interfaces for service abstractions

**In Progress:**
- Controller API endpoints for device provisioning/revocation
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
```

### Running the Application Locally

#### Backend

The backend is a Python application. To run it locally:

```bash
# Ensure virtual environment is activated
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (if not already installed)
pip install -r requirements.txt
pip install -e .

# Run backend server
# Note: Backend server implementation is in progress
# When available, run with:
# python -m src.backend.server
```

**Note:** The backend server implementation is currently in development. The core services (message relay, conversation API, device registry, etc.) are implemented and tested, but the HTTP server wrapper is pending.

#### Frontend (UI)

The frontend is a React + TypeScript application. To run it locally:

```bash
# Navigate to UI directory
cd src/ui

# Install Node.js dependencies (if package.json exists)
# npm install

# Run development server
# npm start
# or
# npm run dev
```

**Note:** The frontend UI implementation is currently in development. The React components are implemented, but the build configuration and development server setup are pending.

#### Full Stack Development

For full-stack development, you'll need to run both backend and frontend:

```bash
# Terminal 1: Backend
source venv/bin/activate
# python -m src.backend.server  # When available

# Terminal 2: Frontend
cd src/ui
# npm start  # When available
```

**Current Status:**
- Backend services: ✅ Implemented and tested
- Backend HTTP server: ⏳ Pending
- Frontend React components: ✅ Implemented
- Frontend build/dev server: ⏳ Pending
- API integration: ⏳ Pending

See [ROADMAP.md](ROADMAP.md) for current development status.

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
