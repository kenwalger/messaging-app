Asset #13 — Copy Rules
Project: Abiqua Asset Management (AAM)
Document Version: 1.0
Status: Frozen
1. Purpose

This document defines all approved text strings for:

UI labels

Buttons and menus

Error messages

System feedback

Operational logs

All copy must:

Be neutral and professional

Avoid spy, secrecy, or marketing metaphors

Be deterministic, reflecting system state exactly

Avoid exposing sensitive or encrypted information

2. Copy Principles

Neutrality: Words like “secure,” “hidden,” “private,” or “spy” must not appear.

Consistency: Same action/state uses same wording throughout the UI.

Clarity: Short, functional phrases preferred.

Error Feedback: Only neutral, deterministic feedback allowed.

3. UI Labels & Buttons
Component	Approved Text
App Splash Screen	“Welcome to Enterprise Messaging”
Conversation List Header	“Conversations”
Send Button	“Send”
Message Input Placeholder	“Type your message”
Device Disabled / Revoked	“Messaging Disabled”
Settings Menu	“Settings”
Logout Button	“Log Out”
Conversation Empty	“No messages yet”
4. Error Messages
Scenario	Approved Copy
Network unavailable	“Unable to send messages; retry will occur automatically”
Backend unreachable	“Unable to connect; retry will occur automatically”
Expired message	Message disappears silently; no copy
Unauthorized / revoked device	“Messaging Disabled”
Invalid input (e.g., blank message)	“Cannot send empty message”
Failed provisioning	“Device provisioning failed; contact administrator”
5. System Feedback & Notifications
Feedback	Approved Copy
Message queued	“Queued”
Message delivered (internal)	No visible copy; metadata only
Device provisioning successful	“Device successfully provisioned”
Device revoked	“Messaging Disabled”
6. Logging & Operational Messages

All logs must be content-free

Only permitted log entries:

device_provisioned

device_revoked

message_attempted (no content)

policy_enforced

Log text should match neutral terminology above

7. Copy Formatting Rules

Sentence case only (first letter capitalized).

Avoid punctuation beyond standard periods.

Do not include system-generated identifiers in user-facing copy.

Strings must be static; no dynamic insertion of sensitive info.

8. TBD Values

None at this stage; all strings are frozen as-is.

9. Summary Statement

All copy for Abiqua is deterministic, neutral, and fully compliant.
No creative or security-themed language is allowed.
Cursor or developers must use only the approved strings in UI, logs, and messages.

End of Copy Rules Specification