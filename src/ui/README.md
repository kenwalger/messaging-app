# Read-Only UI Shell

**References:**
- UX Behavior (#12)
- Copy Rules (#13)
- UI Domain Adapter Layer (latest)
- Resolved Specs & Clarifications

## Overview

This directory contains the read-only UI shell for Abiqua, implemented using React + TypeScript + Tailwind CSS.

The UI shell:
- Consumes UI domain models only (no direct API calls)
- Enforces UX behavior and copy rules visually
- Provides read-only display of conversations and messages
- No message sending, no WebSocket usage, no API calls

## Components

### StatusIndicator
Displays device status with read-only mode indicator.
- Props: `status`, `isReadOnly`
- Per UX Behavior (#12), Section 3.1 and 3.5

### ConversationList
Displays active conversations only in reverse chronological order.
- Props: `conversations`, `onSelectConversation?`, `isReadOnly`
- Per UX Behavior (#12), Section 3.2

### MessageList
Displays messages in reverse chronological order (newest first).
- Props: `messages`, `conversationId`, `isReadOnly`
- Per UX Behavior (#12), Section 3.3 and 3.4

### MessageRow
Displays individual messages with visual distinction for states.
- Props: `message`, `isReadOnly`
- Per UX Behavior (#12), Section 3.3 and 3.4

### App
Main application component that orchestrates the UI shell.
- Props: `deviceState`, `conversations`, `messagesByConversation`
- Per UX Behavior (#12), Section 3.1

## TypeScript Types

All UI domain models are typed in `types.ts`, mirroring the Python UI domain models.

## Mock Data

Mock data fixtures are provided in `fixtures/mockData.ts` for:
- Active device state
- Revoked device state (read-only mode)
- Sample conversations
- Sample messages (including expired and failed states)

## Testing

Unit tests should validate:
1. Correct rendering by state (delivered, failed, expired)
2. Reverse chronological ordering (newest first)
3. Neutral mode visual enforcement (read-only indicators)
4. Expired message filtering (removed automatically)
5. Failed message distinction (explicitly distinguishable)

## Setup

To use this UI shell:

1. Install dependencies:
   ```bash
   npm install react react-dom typescript tailwindcss
   ```

2. Configure Tailwind CSS (see Tailwind documentation)

3. Import and use components:
   ```typescript
   import { App } from './src/ui/App';
   import { mockActiveDeviceState, mockConversations, mockMessages, mockMessageApi, mockWebSocketTransport } from './src/ui/fixtures/mockData';
   import { createMessageTransport } from './src/ui/services/transportFactory';
   
   // Create transport (WebSocket preferred, REST polling fallback)
   const transport = createMessageTransport({
     wsUrl: "wss://api.example.com/ws",
     apiUrl: "https://api.example.com",
     preferredTransport: "websocket",
   });
   
   <App
     deviceState={mockActiveDeviceState}
     conversations={mockConversations}
     messagesByConversation={mockMessages}
     messageApi={mockMessageApi}
     messageTransport={transport}
   />
   ```

## Incoming Message Handling

The UI shell supports incoming messages via:

- **WebSocket Transport** (preferred): Real-time message delivery
- **REST Polling Transport** (fallback): Polls every 30 seconds

Both transports:
- Use X-Device-ID for authentication per API Contracts (#10)
- Handle deduplication automatically
- Preserve reverse chronological ordering
- Support reconnection with automatic reconciliation

Messages appear automatically in the UI without page reload.

## Constraints

- No message sending
- No WebSocket usage
- No API calls
- No side effects
- No speculative UI states
- No sound, no animation, no urgency cues
- Neutral, enterprise-safe visual tone

## Deterministic UX Rules

- Reverse chronological message order (newest at top) per Resolved Clarifications (#53)
- Read-only mode indicators when neutral enterprise mode is active per Resolved Clarifications (#38)
- Visual distinction for delivered/failed/expired messages per UX Behavior (#12), Section 3.4 and 3.6
- Expired messages removed automatically; no undo per UX Behavior (#12), Section 3.3
- Failed messages explicitly distinguishable per UX Behavior (#12), Section 3.6
