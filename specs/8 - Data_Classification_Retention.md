Asset #8 — Data Classification & Retention
Project: Abiqua Asset Management (AAM)
Document Version: 1.0
Status: Frozen
1. Purpose

This document defines:

Data types in AAM

Classification levels (sensitivity)

Retention periods and destruction policies

It ensures all AI agents, developers, and system components treat data deterministically and lawfully.

2. Data Classification Levels
Level	Description	Allowed Storage / Handling
Confidential	Plaintext messages, cryptographic keys, identity bindings	Encrypted at rest, never logged, device-only except encrypted relay
Restricted	Delivery metadata (e.g., timestamps, recipient IDs)	Encrypted in transit, minimal retention, backend relay only for delivery
Internal	Operational logs (start/stop events, provisioning/revocation events)	Can be logged and persisted for auditing, content-free
Public	App version, UI labels, system status messages	Displayed in UI, non-sensitive
3. Data Types & Classification
Data Type	Classification	Location	Retention Policy
Message Content	Confidential	Device	Until expiration; delete from device and relay
Message Metadata (sender/recipient IDs, timestamp)	Restricted	Backend relay	Discard immediately after delivery; never persist post-expiration
Conversation Membership	Restricted	Backend	Remove when conversation ends or participant revoked
Cryptographic Keys	Confidential	Device secure keystore	Rotate per key lifecycle; delete on revocation
Device Identity Binding	Confidential	Device, provisioning DB	Delete on revocation
Audit Logs (events only)	Internal	Backend	Retain per organizational policy (e.g., 30–90 days); no content
App Version / System Labels	Public	Device	Persist indefinitely
4. Retention & Expiration Rules

Message content:

Exists only until expiration timestamp

Must be deleted irreversibly from all device storage

Backend relay only handles encrypted content temporarily

Message metadata:

Used for delivery only

Delete immediately after message is delivered or expired

Conversation records:

Active conversations are retained while participants exist

Deleted when all participants leave or are revoked

Keys & identity:

Rotate keys according to organizational schedule

Delete upon device revocation or decommission

Operational logs:

Content-free

Retention limited by policy

Purge automatically after retention window

5. Data Handling Principles

Encryption: All confidential and restricted data must be encrypted at rest and in transit.

No plaintext in logs: Sensitive content may never appear in logs.

Device-local enforcement: Expiration timers and deletion occur on the device independently.

Backend relay: Handles encrypted messages only; never stores plaintext.

Zero assumption: Do not invent retention, caching, or backup policies beyond what is specified.

6. Edge Case Handling
Scenario	Required Behavior
Device offline during expiration	Delete message when device comes online
Clock skew	Use local time; maintain expiration enforcement
Message delivery failure	Retry within expiration window; discard afterwards
Device revoked while messages pending	Delete all local messages immediately; stop delivery attempts
7. TBD Values (Must Be Defined Before Implementation)

Exact default message expiration duration (e.g., 24h, 7d)

Operational log retention window (e.g., 30 days)

Key rotation schedule (time-based or event-based)

8. Summary Statement

All AAM data is classified, handled, and retained according to deterministic rules.
Confidential content is never stored beyond its defined lifetime.
Any unspecified retention behavior does not exist.

End of Data Classification & Retention Specification