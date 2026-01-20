Non-Goals & Prohibited Behaviors Specification
Project

Abiqua Asset Management (AAM)

Document Version

1.0

Status

Frozen (post-PRD)

1. Purpose of This Document

This document defines explicit non-goals and prohibited behaviors for AAM.

Any implementation, suggestion, or inferred behavior that violates this document must be rejected, even if:

It appears technically sound

It improves usability

It increases “security” in isolation

It is common in other secure messaging products

This document takes precedence over convenience.

2. Explicit Non-Goals

AAM is not designed to:

2.1 Anonymity & Identity Obfuscation

Provide anonymous accounts

Mask user identity from the organization operating AAM

Support burner-style identity creation

Enable identity rotation without administrative control

AAM assumes known, provisioned participants, not anonymous actors.

2.2 Lawful Access Evasion

Evade court orders

Bypass lawful intercept requirements

Obstruct compliance with applicable regulations

Conceal system existence from platform owners or employers

AAM may minimize retained data, but does not actively resist lawful process.

2.3 Covert Distribution or Hidden Installation

No sideloading guidance

No stealth installation techniques

No self-propagation

No installation without informed consent

AAM is not a covert implant.

2.4 Platform or OS Subversion

No OS-level exploit usage

No sandbox escape attempts

No bypassing mobile OS security features

No root or jailbreak dependency

AAM operates within supported platform boundaries.

2.5 Consumer Messaging Parity

No read receipts

No typing indicators

No emoji reactions

No stickers, GIFs, or media-heavy UX

No social graph discovery

AAM is deliberately boring.

2.6 Metadata Erasure Guarantees

No claims of “zero metadata”

No traffic fingerprint obfuscation guarantees

No anonymity network operation (e.g., Tor-like routing claims)

AAM reduces metadata exposure but does not eliminate it.

3. Prohibited Functional Behaviors

The following behaviors must not exist in any implementation.

3.1 Message Handling

No indefinite message retention

No message forwarding

No server-side message indexing

No server-side message search

No message recovery after expiration

3.2 Logging & Telemetry

No logging of message content

No logging of cryptographic material

No analytics SDKs

No third-party telemetry

No “debug logs” containing sensitive state

3.3 Authentication & Identity

No username/password login

No SMS-based authentication

No email-based authentication

No self-service account creation

All identity is provisioned, not registered.

3.4 UX & Disclosure

No UI labels implying secrecy, espionage, or concealment

No “secure mode” branding

No warnings that reveal hidden functionality

No failure states that expose system capabilities

Failure must degrade gracefully into neutral enterprise behavior.

4. Prohibited Technical Shortcuts

Cursor and any sub-agent must not:

Invent cryptographic algorithms

Modify cryptographic parameters ad hoc

Store secrets outside approved secure storage

Add undocumented data fields “for convenience”

Cache sensitive state beyond defined lifetimes

5. Enforcement Rules for AI Agents

If an AI agent encounters a scenario where:

A feature is undefined

A behavior is ambiguous

A tradeoff is required

The agent must STOP and ask for clarification.

Agents must not “fill in the blanks.”

6. Precedence

In case of conflict, precedence is:

Legal / Ethical Constraints (future asset)

This document (Non-Goals & Prohibited Behaviors)

PRD

Functional Specification

Implementation details

7. Summary Statement (for Cursor Context)

AAM prioritizes control, minimization, and predictability over convenience, anonymity, or feature richness.
Any deviation from this philosophy is a defect.

End of Document