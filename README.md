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

**Current Phase:** Frontend Development Server (Completed) - Full-stack development ready

**Completed:**
- Frontend Development Server
  - Vite-based development server with React + TypeScript
  - Hot reload enabled, runs on `http://localhost:5173`
  - Environment variable support (`VITE_API_BASE_URL`)
  - HTTP message API service implementation
  - WebSocket and REST polling transport support
  - Tailwind CSS configured and integrated
  - TypeScript strict mode enabled
- Backend Server Infrastructure
  - Minimal FastAPI server wrapper with all API endpoints wired to existing services
  - WebSocket support for real-time message delivery
  - Health check endpoint
  - Server runs on `http://127.0.0.1:8000` by default
- Controller API endpoints for device provisioning and revocation
  - POST /api/device/provision: Creates device in Pending state
  - POST /api/device/provision/confirm: Transitions Pending → Provisioned
  - POST /api/device/revoke: Revokes device immediately and irreversibly
  - Controller authentication via API key (X-Controller-Key header)
  - Comprehensive unit tests (19 test cases)
  - Controller API documentation with Mermaid diagrams
- Visible messaging UI with store-connected view
  - MessagingView component subscribing to message store
  - Conversation list with last message preview
  - Message pane in chronological order
  - Live updates when store state changes
  - Delivery state indicators
- Message store hardening with comprehensive TypeScript tests
  - Enhanced deduplication and ordering guarantees
  - Reconnection reconciliation support
  - Transport switching safety
  - Comprehensive test coverage (30+ test cases)
- Incoming message handling and live updates
  - Transport abstraction (WebSocket + REST polling)
  - Message deduplication and ordering
  - State reconciliation
  - Automatic UI updates
  - Connection lifecycle handling
- Interactive messaging (send path only)
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

**Backend Tests (Python/pytest):**

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

**Frontend Tests (TypeScript/Vitest):**

Frontend tests use Vitest and are located in `src/ui/__tests__/`:

```bash
# Navigate to UI directory
cd src/ui

# Install dependencies (if not already installed)
npm install

# Run all tests
npm test

# Run in watch mode (for development)
npm test -- --watch

# Run with coverage
npm test -- --coverage

# Run specific test file
npm test -- __tests__/MessageComposer.test.tsx
```

**Test Status:**
- Backend: ✅ All tests passing (118+ tests)
- Frontend: ✅ All tests passing (110 tests)
npm test -- --coverage

# Run specific test file
npm test -- compositeTransport.test.ts
npm test -- sendPath.test.ts
```

**Frontend Test Coverage:**
- Component tests (MessageComposer, MessageList, ConversationList, etc.)
- Service tests (messageStore, messageHandler, compositeTransport)
- Integration tests (sendPath, compositeTransport)
- All tests use React Testing Library and Vitest

#### Integration Testing

End-to-end integration tests verify the complete message lifecycle across backend and frontend boundaries:

**Test Coverage:**
- Message send → ACK happy path (full lifecycle from send to delivery)
- WebSocket preferred transport (verifies WebSocket delivery when available)
- REST fallback simulation (verifies REST polling when WebSocket unavailable)
- Reverse chronological ordering (verifies message ordering is maintained)
- Backend API endpoint integration (verifies /api/message/send endpoint behavior)

**Test Status:**
- All backend E2E tests passing (142/142)
- All frontend tests passing (110/110)
- Tests use deterministic timestamps and fixed message IDs for reliability

**Running Integration Tests:**
```bash
# Run all integration tests
pytest tests/test_e2e_message_lifecycle.py

# Run with verbose output
pytest -v tests/test_e2e_message_lifecycle.py

# Run specific test
pytest tests/test_e2e_message_lifecycle.py::TestE2EMessageLifecycle::test_message_send_to_ack_happy_path
```

**Test Characteristics:**
- **Deterministic**: Uses fixed timestamps and predictable message IDs
- **Happy paths only**: Focuses on successful flows to avoid flakiness
- **No UI/DOM assertions**: Verifies state via stores/services, not DOM
- **No timing sleeps**: Uses deterministic timers and mocks
- **Cross-boundary**: Tests integration between backend and frontend services

**Test Scenarios:**
1. **Message Send → ACK**: Full lifecycle from message creation through delivery and ACK
2. **WebSocket Transport**: Verifies WebSocket is used when available, REST polling not activated
3. **REST Fallback**: Verifies REST polling receives messages when WebSocket unavailable, deduplication works
4. **Message Ordering**: Verifies reverse chronological ordering (newest first) is maintained
5. **Backend API Integration**: Verifies backend endpoint derives recipients from conversation, enqueues messages

### Deployment to Heroku

The application can be deployed to Heroku for live multi-device demos. See [DEPLOYMENT.md](DEPLOYMENT.md) for complete deployment instructions.

**Quick Start:**
```bash
# Create Heroku app
heroku create abiqua-asset-management

# Set buildpacks (Node.js first, then Python)
heroku buildpacks:add --index 1 heroku/nodejs
heroku buildpacks:add --index 2 heroku/python

# Add Heroku Redis addon (required for persistent conversation storage)
heroku addons:create heroku-redis:mini

# Set environment variables
heroku config:set ENCRYPTION_MODE=client
heroku config:set FRONTEND_ORIGIN=https://abiqua-asset-management.herokuapp.com
heroku config:set ENVIRONMENT=production
heroku config:set DEMO_MODE=true  # Enable demo mode for reliable multi-device demos
heroku config:set CONVERSATION_TTL_SECONDS=1800  # Optional: 30 minutes (default)

# Deploy
git push heroku main
```

**Key Features:**
- Single dyno deployment (backend serves frontend static files)
- **Redis-backed conversation storage** (persists across dyno restarts and multiple dynos)
- WebSocket support (native Heroku WebSocket support, best-effort delivery in demo mode)
- Multi-device support (each browser generates unique device ID, stored in localStorage)
- Dynamic conversation creation (auto-creates conversation on first load)
- Join conversation flow (share conversation ID to join from multiple devices)
- Encryption mode configurable via `ENCRYPTION_MODE` environment variable
- **Demo Mode**: HTTP-first messaging with lenient device validation (enabled via `DEMO_MODE=true`)
- Automatic fallback to in-memory store in demo mode when Redis unavailable

**Demo Mode:**
Demo mode (`DEMO_MODE=true`) enables reliable multi-device demos on Heroku by:
- Allowing HTTP-first messaging without WebSocket dependency
- Auto-registering devices on first request
- Using device activity TTL (5 minutes) instead of strict active state checks
- Making WebSocket delivery best-effort (messages always queued for REST polling)
- Not blocking message sends based on WebSocket connection status
- Preserving encryption requirements (client or server mode enforced)

**Multi-Device Demo Flow:**
1. First device opens app → generates unique device ID → auto-creates conversation → displays conversation ID in sidebar
2. Second device opens app → generates different device ID → user copies conversation ID from first device → pastes in "Join Conversation" field → clicks "Join"
3. After joining, the conversation is automatically selected and ready for messaging
4. Conversation ID display in sidebar updates to show the currently selected conversation (can be copied with "Copy" button)
3. All devices share same conversation → messages delivered via WebSocket (if available) or REST polling → real-time updates

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions, troubleshooting, and live demo checklist.

### Running the Application Locally

#### Backend Server

The backend server can be started using uvicorn:

```bash
# Activate virtual environment (if not already active)
source venv/bin/activate

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Run the server
uvicorn src.backend.server:app --reload

# Or run directly
python -m src.backend.server
```

The server will start on `http://127.0.0.1:8000` by default.

**Available Endpoints:**
- Health check: `GET /health`
- Controller API: `POST /api/device/provision`, `POST /api/device/provision/confirm`, `POST /api/device/revoke`
- Conversation API: `POST /api/conversation/create`, `POST /api/conversation/join`, `POST /api/conversation/leave`, `POST /api/conversation/close`, `GET /api/conversation/info`
  - `POST /api/conversation/create`: Creates a new conversation
    - Request body: `{"participants": ["device-001", "device-002"]}` (JSON object with `participants` array)
    - Automatically includes calling device (from `X-Device-ID` header) in participants if not present
    - Returns: `{"conversation_id": "<uuid>", "participants": [...], "status": "success"}`
    - Returns existing conversation if conversation with same ID already exists (idempotent)
    - Rejects empty participant lists with 400 Bad Request
- Message API: `POST /api/message/send`, `GET /api/message/receive`
- Logging API: `POST /api/log/event`
- WebSocket: `WS /ws/messages` (for real-time message delivery)

#### Environment Variables

- `ENCRYPTION_MODE`: Encryption mode configuration (default: `client`)
  - `client`: Require hex or base64 encoded encrypted payloads (production mode)
  - `server`: Accept plaintext payloads, encrypt server-side (dev/POC mode only)
- `ENCRYPTION_KEY_SEED`: Seed for server-side encryption key (dev/POC mode only, default: `dev-mode-encryption-key-seed`)
- `ENVIRONMENT`: Environment mode (default: `development`)
- `REDIS_URL`: Redis connection URL for persistent conversation storage (Heroku Redis addon)
  - If not set and `DEMO_MODE=true`: Falls back to in-memory store (state lost on restart)
  - If not set and `DEMO_MODE=false`: Raises error (Redis required for production)
  - Automatically detected from Heroku Redis addon
- `CONVERSATION_TTL_SECONDS`: Time-to-live for conversations in Redis (default: 1800 seconds / 30 minutes)
  - Conversations automatically expire after TTL
  - Configurable for different retention policies
  - `development`, `dev`, `local`: Development mode (permissive CORS, auto-provisioning)
  - `production`: Production mode (strict CORS, no auto-provisioning)

#### Frontend (UI)

The frontend is a React + TypeScript application using Vite. To run it locally:

**Prerequisites:**
- Node.js >= 18.0.0

**Setup:**

```bash
# Navigate to UI directory
cd src/ui

# Install Node.js dependencies
npm install

# Configure API base URL (optional, defaults to http://127.0.0.1:8000)
# Create .env file or set environment variable:
export VITE_API_BASE_URL=http://127.0.0.1:8000

# Run development server
npm run dev
```

The frontend will start on `http://localhost:5173` by default.

**Environment Configuration:**

The frontend uses the `VITE_API_BASE_URL` environment variable to configure the backend API endpoint:

- **Default**: `http://127.0.0.1:8000` (if not set)
- **Set via `.env` file**: Create `src/ui/.env` with `VITE_API_BASE_URL=http://127.0.0.1:8000`
- **Set via environment variable**: `export VITE_API_BASE_URL=http://127.0.0.1:8000`

The WebSocket URL is automatically derived from the API base URL (replaces `http` with `ws` and appends `/ws/messages`).

#### Frontend ↔ Backend Integration

The frontend automatically connects to the backend on startup. The integration flow:

1. **Health Check**: On app startup, the frontend calls `GET /health` to verify backend availability (development logging only).

2. **Device State**: Device state is derived by checking if the device can receive messages via `GET /api/message/receive`. If the device can receive messages, it's considered active. If unauthorized (401/403), it's considered revoked.

3. **Message Fetching**: Initial messages are fetched via `GET /api/message/receive` to populate conversations and message history.

4. **Conversation Info**: For each unique conversation ID found in messages, the frontend calls `GET /api/conversation/info` to get conversation details (participants, state, etc.).

5. **WebSocket Connection**: The frontend establishes a WebSocket connection to `/ws/messages` for real-time message delivery. The device ID is passed as a query parameter (`?device_id=<device_id>`).

**Required Backend Headers:**
- `X-Device-ID`: Required for all API endpoints (device authentication)
- `X-Controller-Key`: Required for Controller API endpoints (device provisioning/revocation)

**Controller Setup (if applicable):**
For device provisioning and revocation, you'll need to set the `CONTROLLER_API_KEYS` environment variable:

```bash
export CONTROLLER_API_KEYS=your-controller-key-1,your-controller-key-2
```

If not set, the backend defaults to `test-controller-key` for development (with a warning log).

**CORS Configuration:**
The backend automatically enables CORS for local development to allow the frontend (running on `http://localhost:5173` or `http://127.0.0.1:5173`) to make REST API calls and establish WebSocket connections.

- **Development Mode (Default)**: CORS is enabled with permissive settings:
  - Allowed origins: `http://localhost:5173`, `http://127.0.0.1:5173`
  - Allowed methods: `GET`, `POST`, `OPTIONS`
  - Allowed headers: `Content-Type`, `Authorization`, `X-Device-ID`, `X-Controller-Key`
  - Credentials: `false` (not required for local development)
- **Production Mode**: Set `ENVIRONMENT=production` to disable CORS (strict security)
  - CORS middleware is not added in production mode
  - Cross-origin requests will be rejected (use reverse proxy for production)

**Device Auto-Provisioning (Development Mode):**
In development mode, devices are automatically provisioned when they connect via WebSocket. This eliminates the need to manually provision devices via the Controller API for local development.

- **Development Mode (Default)**: Devices are auto-registered, provisioned, and activated when connecting via WebSocket
- **Production Mode**: Set `ENVIRONMENT=production` to disable auto-provisioning (devices must be provisioned via Controller API first)

**Expected Local Dev Flow:**
1. Start backend server in Terminal 1:
   ```bash
   source venv/bin/activate
   uvicorn src.backend.server:app --reload
   ```

2. Start frontend dev server in Terminal 2:
   ```bash
   cd src/ui
   npm run dev
   ```

3. The frontend will automatically:
   - Check backend health on startup (CORS headers included)
   - Fetch device state, messages, and conversations (CORS preflight handled)
   - Establish WebSocket connection for real-time updates (device_id via query param)
   - **Auto-provision device** if not already provisioned (development mode only)
   - Fall back to mock data if backend is unavailable

**Error Handling:**
- All errors are normalized via existing adapter logic
- Error messages remain neutral and content-free (per Copy Rules #13)
- No stack traces or backend details are exposed to users
- Network errors are handled silently with automatic retries

#### WebSocket Resilience

The frontend implements automatic resilience for WebSocket connections:

**Reconnect Behavior:**
- WebSocket automatically reconnects with exponential backoff (1s, 2s, 4s, 8s, ... up to 60s max)
- No manual refresh required - reconnection happens automatically
- Reconnect attempts are logged in development mode only (no content exposed)

**REST Polling Fallback:**
- If WebSocket is unavailable for >15 seconds, the frontend automatically falls back to REST polling
- REST polling fetches messages every 30 seconds via `GET /api/message/receive`
- Fallback activation is logged in development mode only

**Transport Switching:**
- REST polling stops immediately when WebSocket reconnects (WebSocket is preferred)
- Messages are deduplicated by message ID to prevent duplicates when switching transports
- The UI does not care which transport is active - messages appear seamlessly

**Message Deduplication:**
- Messages are deduplicated by message ID in the message store
- Prevents duplicate messages when the same message arrives via both WebSocket and REST polling
- State reconciliation ensures message states transition correctly (sent → delivered → failed)

#### Sending Messages (Interactive Path)

The frontend implements an interactive message send path with optimistic updates:

**Message Composition:**
- User composes message in `MessageComposer` component
- Payload validation occurs before send (empty/whitespace-only messages rejected)
- Content is trimmed before sending

**Optimistic Updates:**
- Message immediately appears in UI as "Queued" (PENDING state) when Send is clicked
- Message ordering remains correct (reverse chronological, newest first)
- No duplicate local insertion (deduplication handled by message store)

**API Call:**
- Frontend calls `POST /api/message/send` with required fields:
  - `conversation_id`: Conversation identifier (REQUIRED - always included in request body)
  - `payload`: Message payload (encoding depends on `ENCRYPTION_MODE`):
    - `ENCRYPTION_MODE=client` (default/production): Must be hex or base64 encoded encrypted bytes
    - `ENCRYPTION_MODE=server` (dev/POC only): Can be plaintext; server encrypts before persistence/delivery
  - `encryption`: Encryption mode indicator (optional, for backend logging/diagnostics: "client" or "server")
  - `expiration`: ISO 8601 timestamp (optional, defaults to server timestamp + 7 days)
- Backend validates request using Pydantic `SendMessageRequest` model (ensures conversation_id is present)
- Backend assigns `message_id` server-side (UUID v4)
- Backend uses server timestamp (not client-provided)
- Backend logs received conversation_id for debugging
- `X-Device-ID` header for device authentication
- Backend validates request:
  - Required fields present (message_id, conversation_id, payload, timestamp)
  - Message ID is valid UUID v4
  - Timestamp validation:
    - Timestamp is not expired (with 2-minute clock skew tolerance)
    - Timestamp is not too far in the future (rejects timestamps beyond clock skew tolerance)
  - Payload size ≤ 50KB (enforced per MAX_MESSAGE_PAYLOAD_SIZE_KB constant)
  - Payload encoding validation:
    - `ENCRYPTION_MODE=client` (default): Payload must be hex or base64 encoded encrypted bytes
    - `ENCRYPTION_MODE=server` (dev/POC): Payload can be plaintext; server encrypts before persistence/delivery
  - Conversation exists (returns 404 if not found)
  - Conversation is in ACTIVE state (returns 400 if inactive)
  - **Authorization**: Sender must be a participant in the conversation (returns 403 Forbidden if not a participant)
- Backend enqueues message for delivery:
  - Message enters PendingDelivery state
  - Recipients derived from conversation participants (excluding sender)
  - Message forwarded to WebSocket recipients if connected, otherwise queued for REST polling
  - ACK timer started (30s timeout)
  - Returns 202 Accepted with `{"status": "accepted", "message_id": "<uuid>"}`
- Backend logging (metadata only, no content):
  - Logs message send attempts using `LogEventType.MESSAGE_ATTEMPTED`
  - Logs delivery failures using `LogEventType.DELIVERY_FAILED`
  - Logged fields: message_id, conversation_id, sender_id, recipient_count, message_size_bytes, timestamp
  - No message content, keys, or sensitive data logged per Logging & Observability (#14)

**Delivery State Transitions:**
- **PENDING → DELIVERED**: When delivery succeeds (via ACK mechanism)
- **PENDING → FAILED**: When delivery fails (network error, backend unavailable)
- State transitions update UI automatically without refresh
- No reordering occurs during state transitions

**Failure Handling:**
- Network failures handled gracefully (message transitions to FAILED state)
- Backend unavailable errors handled silently
- No retry UI exposed (automatic retries handled by backend)
- UI remains consistent and usable after failures

**Disabled Send Conditions:**
- **Neutral enterprise mode**: Send button disabled when device is revoked
- **Closed conversation**: Send button disabled when conversation is closed
- **Read-only device**: Send button disabled when device cannot send
- Clear but neutral explanation shown (no error messages)
- No API call attempted when send is disabled

**Logging & Observability:**
- Send attempts logged (metadata only, no message content)
- Failure events are observable via logging service
- No message content logged or leaked per Logging & Observability (#14)

**End-to-End Message Delivery Flow:**

1. **Message Send (Frontend → Backend)**:
   - User types message in UI and clicks send
   - Frontend ALWAYS includes conversation_id in request body (does not rely on implicit state)
   - Frontend validates conversation_id is present before sending
   - Message sent via `POST /api/message/send` (HTTP, not WebSocket for sending)
   - Backend validates request using Pydantic model (ensures conversation_id is required)
   - Backend logs received conversation_id for debugging
   - Backend validates device is active, conversation exists and is active, sender is participant
   - Backend returns 400 (not 404) if conversation_id is missing or conversation not found
   - Backend assigns message_id (UUID v4) and uses server timestamp
   - Backend enqueues message for delivery
   - Frontend optimistically updates UI with message in PENDING state ("Queued")

2. **Message Delivery (Backend → Recipient)**:
   - Backend attempts WebSocket delivery (preferred) to recipient
   - If WebSocket unavailable, message queued for REST polling
   - Recipient receives message via WebSocket or REST polling
   - Recipient automatically sends ACK to backend via WebSocket

3. **ACK Handling (Recipient → Backend → Sender)**:
   - Backend receives ACK from recipient
   - Backend forwards ACK to sender via WebSocket
   - Sender's frontend receives ACK and updates message state: PENDING → DELIVERED
   - UI updates automatically (no refresh needed)

4. **Message State Transitions**:
   - **PENDING** (sent): Message sent, waiting for delivery confirmation
   - **DELIVERED**: Message delivered to recipient (ACK received)
   - **ACTIVE**: Message received by recipient (for incoming messages)
   - **FAILED**: Message delivery failed (network/backend error)

**Testing End-to-End Flow:**

1. Open two browser windows/tabs to `http://localhost:5173`
2. In each window, ensure devices are provisioned and in a conversation
3. Send a message from Window 1
4. Verify in Window 1: Message appears immediately in "Queued" state
5. Verify in Window 2: Message appears in conversation (received via WebSocket)
6. Verify in Window 1: Message state transitions from "Queued" to "Delivered" (ACK received)
7. Verify message ordering: Newest messages appear first (reverse chronological)

#### Manual Testing Checklist

For developer-facing manual testing and debugging:

**Connection Status Observation:**
1. **Check Connection Indicator**: Look at the status bar at the top of the sidebar
   - Should show "WebSocket connected" when backend is running
   - Should show "WebSocket reconnecting" if connection drops
   - Should show "REST polling" when WebSocket unavailable >15s
2. **Kill Backend Briefly**: Stop the backend server (Ctrl+C)
   - Observe connection indicator change to "Disconnected" or "REST polling"
   - Send button should be disabled when disconnected
3. **Restart Backend**: Start the backend server again
   - Observe connection indicator return to "WebSocket connected"
   - Send button should be enabled again

**Message State Visibility:**
1. **Send a Message**: Type and send a message
   - Message should appear immediately with italic text and 🕐 (Queued) indicator
   - Message should show PENDING state visually
2. **Observe State Transition**: Wait for ACK (typically <1 second)
   - Message text should change from italic to normal
   - 🕐 indicator should disappear
   - Message should show DELIVERED state
3. **Test Failure Scenario**: Stop backend before sending
   - Send button should be disabled (connection status prevents send)
   - If message fails, it should show ⚠ (Failed) indicator with muted styling

**Debug Mode:**
1. **Enable Debug Mode**: Click "Show" button in "Debug Mode" section of sidebar
2. **View Message Metadata**: Each message should now show:
   - Message ID (UUID)
   - State (sent, delivered, failed, expired)
   - Created timestamp (ISO format)
   - Expiration timestamp (ISO format)
3. **Disable Debug Mode**: Click "Hide" to return to normal view

**UX Guardrails:**
1. **Send Button States**:
   - Disabled when no conversation selected
   - Disabled when connection is "connecting" or "disconnected"
   - Disabled when device is read-only or conversation is closed
   - Disabled when message content is empty
   - Shows "Sending..." state during message send (prevents duplicate sends)
2. **Rapid Clicking**: Try clicking send button multiple times rapidly
   - Only one message should be sent (isSending state prevents duplicates)
   - Button should show "Sending..." state during send operation

#### Full Stack Development

For full-stack development, you'll need to run both backend and frontend in separate terminals:

**Terminal 1: Backend Server**
```bash
# Activate virtual environment
source venv/bin/activate

# Start FastAPI server with auto-reload
uvicorn src.backend.server:app --reload

# Server will be available at http://127.0.0.1:8000
```

**Terminal 2: Frontend Development Server**
```bash
# Navigate to UI directory
cd src/ui

# Install dependencies (first time only)
npm install

# Start Vite dev server
npm run dev

# Frontend will be available at http://localhost:5173
```

**Verification:**
1. Backend health check: Open `http://127.0.0.1:8000/health` in browser (should return `{"status":"ok"}`)
2. Frontend connects automatically: Open `http://localhost:5173` - frontend will automatically:
   - Check backend health on startup
   - Fetch device state, messages, and conversations
   - Establish WebSocket connection for real-time updates
   - Fall back to mock data if backend is unavailable

**Testing End-to-End Message Delivery:**

To test the complete message delivery flow:

1. **Setup**: Open two browser windows/tabs to `http://localhost:5173`
2. **Provision Devices**: In each window, ensure devices are provisioned and active
3. **Create/Join Conversation**: Ensure both devices are in the same conversation
4. **Send Message**: In Window 1, type a message and click send
5. **Verify Sender (Window 1)**:
   - Message appears immediately in "Queued" state (optimistic update)
   - Message state transitions to "Delivered" when ACK received (typically <1 second)
6. **Verify Recipient (Window 2)**:
   - Message appears automatically without refresh (WebSocket delivery)
   - Message shows in "Delivered" state
7. **Verify Ordering**: Messages appear in reverse chronological order (newest first)

**Known Limitations (POC Status):**
- Message encryption is not yet implemented (payloads are sent as plaintext)
- Authentication is device-based only (no user authentication)
- Message persistence is in-memory only (messages lost on server restart)
- No message editing or deletion
- No file attachments
- No read receipts beyond delivery ACKs

**Environment Variables:**

**Backend:**
- `CONTROLLER_API_KEYS` (optional): Comma-separated list of controller API keys for device provisioning/revocation. Defaults to `test-controller-key` for development.

**Frontend:**
- `VITE_API_BASE_URL` (optional): Backend API base URL. Defaults to `http://127.0.0.1:8000` if not set.
  - Set via `.env` file: Create `src/ui/.env` with `VITE_API_BASE_URL=http://127.0.0.1:8000`
  - Set via environment variable: `export VITE_API_BASE_URL=http://127.0.0.1:8000`

**Integration Status:**
- ✅ **Message Sending**: Frontend → `POST /api/message/send` → Backend (with `X-Device-ID` header)
- ✅ **Message Receiving**: Backend → `WS /ws/messages` → Frontend (real-time delivery)
- ✅ **Authentication**: `X-Device-ID` header included in all API calls
- ✅ **Optimistic Updates**: Messages appear immediately in UI as "Queued" (PENDING state)
- ✅ **Delivery State Transitions**: PENDING → DELIVERED/FAILED via ACK handling
- ✅ **Error Handling**: Neutral error messages, no content logged (per Copy Rules #13)

**Current Status:**
- Backend services: ✅ Implemented and tested
- Backend HTTP server: ✅ Implemented (FastAPI with all endpoints)
- Frontend React components: ✅ Implemented
- Frontend build/dev server: ✅ Implemented (Vite)
- API integration: ✅ Implemented (HTTP and WebSocket)

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
