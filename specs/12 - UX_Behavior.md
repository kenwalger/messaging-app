Asset #12 — UX Behavior
Project: Abiqua Asset Management (AAM)
Document Version: 1.0
Status: Frozen
1. Purpose

This document defines all user-facing behavior for Abiqua, including:

Screens and workflows

Error states and messaging

Interaction patterns for messaging, identity, and device states

All UX must be deterministic, neutral, and boring — no gamification or secrecy metaphors. Cursor or any developer must not invent any behaviors not explicitly defined here.

2. UX Principles

Neutrality: No language implying covert, spy, or “untraceable” functionality.

Clarity: Only functional, actionable labels are used.

Consistency: State changes are reflected immediately in the UI.

Deterministic Feedback: Actions always produce the same feedback.

No Surprise: UX does not hide errors, but errors are neutral.

3. Operator Device Workflows
3.1 Launch

Show neutral splash screen: “Welcome to Enterprise Messaging”

Authenticate device identity:

Valid: Show main messaging UI

Revoked / invalid: Show neutral “Messaging Disabled” screen

No branding, security indicators, or secret icons appear

3.2 Conversation List

Display active conversations only

Each conversation shows:

Participant names (or IDs if anonymized)

Last message timestamp

Conversations with all participants revoked disappear automatically

3.3 Sending a Message

Select conversation

Enter text in input field

Press Send

UI shows “Queued” until backend acknowledges delivery

No typing indicators, read receipts, or reactions are displayed

Expired messages are removed automatically; no undo

3.4 Receiving a Message

Messages appear in conversation in order of device-local receipt

Message content decrypted locally

Expiration timer starts immediately

No notifications beyond neutral UI update (e.g., conversation bolded)

3.5 Device Revocation / Identity Disabled

UI shows neutral message: “Messaging Disabled”

All secure content removed from view

User cannot access messaging features

Operator may continue to use neutral enterprise features if any exist

3.6 Error Handling
Scenario	UI Feedback
Network unavailable	“Unable to send messages; retry will occur automatically”
Backend unreachable	Same as above
Expired messages	Messages disappear silently
Unauthorized / revoked device	“Messaging Disabled”

Notes: No error codes, no stack traces, no references to encryption.

3.7 Menu / Settings

Only neutral options allowed (e.g., account info, preferences, log out)

No “security dashboard,” “untraceable mode,” or hidden functionality

4. UX States Mapping to State Machines
UX State	Device / Message State
Messaging Disabled	Device Lifecycle = Revoked or Unprovisioned
Active Messaging	Device Lifecycle = Active
Message Queued	Message Lifecycle = PendingDelivery
Message Displayed	Message Lifecycle = Active
Message Removed	Message Lifecycle = Expired

Notes: UX strictly follows underlying state machines; deviations are not allowed.

5. Accessibility & Platform Behavior

UI must be readable, navigable via keyboard / touch / standard accessibility tools

Neutral color scheme (no red/green/security color metaphors)

No hidden gestures or secret interactions

6. TBD Values

Maximum number of messages displayed in conversation view

Default sorting of conversations (e.g., newest first)

Notification behavior (banner vs badge)

7. Summary Statement

Abiqua’s UX is deterministic, neutral, and fully bound to the underlying functional and state specifications.
All feedback, displays, and interaction patterns must reflect system state exactly; no creative or gamified behaviors are allowed.

End of UX Behavior Specification