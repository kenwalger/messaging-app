Asset #5 — “Do Not Invent” List
Project: Abiqua Asset Management (AAM)
Document Version

1.0

Status

Frozen

1. Purpose

This document defines explicit prohibitions against AI invention.

Any AI agent (including Cursor) working on Abiqua Asset Management must not introduce behavior, structure, or assumptions beyond what is explicitly defined in the specifications.

If something is not defined, the correct behavior is to stop and ask.

2. General Rule

If a requirement, field, behavior, or decision is not explicitly specified, it does not exist.

AI agents must not “fill in the blanks.”

3. Prohibited Inventions — Architecture

AI agents must not invent:

Additional services

Background jobs or workers

Message queues

Caches

Analytics pipelines

“Future-proofing” layers

Shadow admin tools

Only explicitly specified components may exist.

4. Prohibited Inventions — Cryptography & Security

AI agents must not invent or modify:

Cryptographic algorithms

Cipher suites

Key sizes

Key derivation methods

Key rotation schedules

Entropy sources

Random number generation logic

Cryptography may only be used as abstracted, vetted primitives per specification.

5. Prohibited Inventions — Identity & Authentication

AI agents must not invent:

Usernames

Passwords

Emails

Phone numbers

MFA methods

Self-service registration

Password recovery flows

Identity exists only as provisioned, device-bound entities.

6. Prohibited Inventions — Messaging Semantics

AI agents must not invent:

Message reactions

Read receipts

Typing indicators

Forwarding

Editing

Message recovery

Message pinning or starring

Cross-conversation search

Messaging behavior is intentionally minimal.

7. Prohibited Inventions — Metadata & Logging

AI agents must not invent:

Additional metadata fields

Persistent identifiers beyond those specified

Correlation IDs that span systems

User analytics

Behavioral tracking

All metadata must be explicitly justified by a spec.

8. Prohibited Inventions — UX & Copy

AI agents must not invent:

Security-themed language

Spy or secrecy metaphors

Warnings that reveal hidden functionality

Error messages implying covert operation

Branding inconsistent with neutral enterprise software

Language must remain boring, neutral, and professional.

9. Prohibited Inventions — Operational Behavior

AI agents must not invent:

Backup strategies for sensitive data

“Just in case” retention

Automatic retries that extend data lifetime

Silent failure recovery that changes semantics

Undocumented admin override capabilities

Operational behavior must be explicit and deterministic.

10. Ambiguity Handling Rule

If an AI agent encounters:

An undefined value

An unspecified limit

A missing timeout

An unclear failure mode

The agent must stop and request clarification.

Proceeding without clarification is a defect.

11. Enforcement Language for Cursor

This block should be included verbatim in Cursor’s system or workspace instructions:

You are not permitted to invent missing requirements.

If a value, behavior, or structure is not explicitly specified,
you must stop and ask for clarification before proceeding.

Assumptions are not allowed.

12. Summary Statement

Abiqua Asset Management prioritizes predictability and control over creativity.
Invention without specification is considered a failure.

End of “Do Not Invent” List