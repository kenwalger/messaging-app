Asset #6 — Functional Specification
Project: Abiqua Asset Management (AAM)
Document Version

1.0

Status

Frozen

1. Purpose

This document defines the exact functional behavior of Abiqua Asset Management.

It answers the question:

“When X happens, exactly what must the system do?”

This specification is:

Deterministic

Complete

Non-creative

Any behavior not described here does not exist.

2. System Actors
2.1 Operator

A provisioned end user

Uses a single, provisioned device

Can send and receive messages

2.2 Controller

Administrative role

Provisions, revokes, and decommissions operators and devices

2.3 System

Enforces all rules

Does not make discretionary decisions

3. Identity & Session Behavior
3.1 Identity Definition

Identity is device-bound

Each device has exactly one identity

Identity cannot be transferred between devices

Identity cannot exist without provisioning

3.2 Session Establishment

Operator launches the application

Application authenticates device identity using secure storage

If identity is valid:

Operator is granted access

If identity is invalid or revoked:

Application enters neutral enterprise-only mode

Secure messaging features are inaccessible

No alternative login methods exist.

4. Messaging Functional Behavior
4.1 Conversation Creation

Conversations are explicitly created

Participants are explicitly defined

Maximum group size is TBD (must be defined before implementation)

No implicit conversation discovery exists.

4.2 Sending a Message

When an operator sends a message:

Message content is encrypted on the device

Message is assigned:

Sender identity

Recipient identity list

Creation timestamp

Expiration timestamp

Encrypted message payload is transmitted

No plaintext leaves the device

4.3 Receiving a Message

When a message is received:

Payload is decrypted locally

Message is stored encrypted at rest on device

Message becomes visible in the UI

Expiration timer begins

4.4 Message Expiration

Each message has an expiration timestamp

Upon expiration:

Message is deleted from device storage

Message is removed from UI

Expired messages cannot be recovered

Expiration is enforced locally and independently on each device.

4.5 Message Failure Handling

If message delivery fails:

The system may retry delivery within the expiration window

After expiration, retries cease

No error details are exposed to the user beyond neutral failure messaging

5. Backend Functional Behavior
5.1 Message Relay

Backend acts as a relay only

Backend never stores plaintext

Backend does not index messages

Backend does not retain messages beyond delivery or expiration

5.2 Metadata Handling

The backend may process:

Routing identifiers

Delivery status

Expiration timestamps

The backend must not persist:

Message content

Cryptographic material

Long-term communication graphs

6. Device Security Behavior
6.1 Local Storage

All sensitive data stored encrypted

Secure keystore used for keys

No sensitive data stored in logs or cache

6.2 Device Loss or Revocation

When a device is revoked:

Backend marks identity as revoked

Application detects revocation on next interaction

Application:

Deletes all local secure data

Disables secure messaging

Remains in neutral enterprise mode

No remote plaintext access exists.

7. UX Functional Behavior
7.1 Normal Operation

UI appears as neutral enterprise software

Secure messaging is accessed through normal workflows

No special visual indicators for security state

7.2 Failure States

Failures degrade functionality gracefully

UI does not indicate:

Encryption state

Hidden features

Security posture

Failure messages are neutral and non-alarming.

8. Logging & Auditing Behavior
8.1 Logged Events (Allowed)

Device provisioning

Device revocation

Application start/stop

Message send attempt (no content)

Policy enforcement events

8.2 Prohibited Logs

Message content

Cryptographic keys

Full message metadata

User behavior analytics

9. Error Handling Rules

Errors must be deterministic

Errors must not leak sensitive information

Errors must not change system behavior beyond defined rules

Silent failure is preferred to verbose error reporting

10. Edge Case Handling
Scenario	Required Behavior
Network unavailable	Queue encrypted payload until expiration
Backend unreachable	Same as above
App backgrounded	Expiration timers continue
Clock skew	Use device time; no server correction
Duplicate delivery	Discard duplicates
11. Forbidden Functional Behaviors

The system must not:

Allow message forwarding

Allow message editing

Allow message recovery

Allow content export

Allow cross-conversation search

12. AI Implementation Guidance

AI agents must:

Implement only described behavior

Not infer missing values

Halt on TBD values

Trace code paths to spec sections

13. Open TBDs (Must Be Resolved Before Implementation)

Maximum group size

Default message expiration

Platform targets (mobile/web)

Offline storage limits

These TBDs block implementation.

14. Summary Statement

Abiqua Asset Management is a deterministic system.
Every behavior is defined, enforced, and bounded.
Anything undefined does not exist.

End of Functional Specification