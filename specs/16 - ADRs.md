Asset #16 — Architecture Decision Records (ADRs)
Project: Abiqua Asset Management (AAM)
Document Version: 1.0
Status: Frozen
1. Purpose

ADRs provide a formal record of architectural decisions, including:

What decision was made

Why it was made (rationale)

Alternatives considered

Consequences and constraints

This ensures consistency and traceability across:

State Machines (#7)

Identity Lifecycle (#11)

UX Behavior (#12)

Logging & Observability (#14)

No decisions outside of these ADRs may be assumed.

2. ADR Template
Field	Description
ADR ID	Unique sequential ID (e.g., ADR-001)
Title	Short descriptive title
Status	Proposed / Accepted / Deprecated
Context	Background and problem statement
Decision	Chosen approach
Alternatives	Other approaches considered
Consequences	Implications, constraints, and trade-offs
Date	Decision date
Author	Decision-maker or team
3. Key ADRs for Abiqua
ADR-001: Device-Bound Identity

Status: Accepted

Context: Messaging must be device-specific and untransferable

Decision: Each device has a unique device_id and key pair; no multi-device identity sharing

Alternatives:

User-based identity across devices → rejected for deterministic offline behavior

Shared device groups → rejected for privacy concerns

Consequences: Deterministic lifecycle; simplifies state machines and revocation

ADR-002: Encrypted-Only Messaging

Status: Accepted

Context: All messages must remain confidential

Decision: Only encrypted payloads are transmitted; backend handles metadata only

Alternatives:

Backend stores plaintext for retries → rejected due to sensitivity

Client-side ephemeral messages without backend → rejected for offline reliability

Consequences: Message confidentiality guaranteed; requires secure key management

ADR-003: Stateless Backend Relay

Status: Accepted

Context: Backend must avoid storing sensitive content

Decision: Relay is stateless regarding content; only handles metadata and delivery

Alternatives:

Stateful relay → rejected due to compliance risks

Consequences: Simplifies compliance; requires deterministic offline retry logic on devices

ADR-004: Message Expiration Enforcement

Status: Accepted

Context: Messages must be removed automatically on expiration

Decision: Device-local timers enforce expiration; expired messages deleted silently

Alternatives:

Backend-enforced expiration → rejected due to offline devices

Consequences: Expired messages cannot be recovered; UX must reflect automatic removal

ADR-005: Logging & Observability

Status: Accepted

Context: Operational visibility required without exposing sensitive data

Decision: Logs are content-free; metrics aggregated; retention per Data Classification

Alternatives:

Full message logging → rejected for compliance

Consequences: Operational monitoring preserved; ensures determinism and auditability

ADR-006: UX Neutrality

Status: Accepted

Context: System must avoid “spy-themed” or gamified UX

Decision: Neutral, deterministic copy only; no hidden features or secret indicators

Alternatives:

Gamified or themed UX → rejected for legal and ethical constraints

Consequences: UX deterministic; supports training, accessibility, and regulatory compliance

4. ADR Maintenance

New ADRs are created for any architectural decision impacting system behavior

Deprecated ADRs must clearly reference the replacement ADR

ADRs are version-controlled in the repo alongside code and specs

5. Summary Statement

ADRs formalize all architectural decisions, providing rationale, alternatives, and deterministic consequences.
Cursor or developers may not invent new architectural assumptions outside of documented ADRs.

End of Architecture Decision Records Specification