Asset #4 — Legal & Ethical Constraints

Project: Abiqua Asset Management (AAM)
Purpose: This document defines the outermost guardrails for both humans and AI agents.
If this document forbids something, nothing downstream may override it.

Legal & Ethical Constraints Specification
Project

Abiqua Asset Management (AAM)

Document Version

1.0

Status

Frozen

1. Purpose

This document establishes the legal, regulatory, and ethical boundaries within which Abiqua Asset Management must operate.

It exists to ensure that:

The system is designed for legitimate, defensible use cases

AI implementation agents do not introduce functionality that could expose operators or users to legal or ethical risk

Product intent remains clear even as implementation details evolve

This document has highest precedence among all specifications.

2. Guiding Principles

AAM is built according to the following principles:

Lawful by Design

The system must be deployable within applicable legal frameworks.

Informed Use

Users and operators must understand what the system does and does not do.

Data Minimization

Retain only what is necessary, for as long as necessary.

Proportional Security

Security controls must align with defined threats, not exceed them for evasion’s sake.

No Deceptive Functionality

The system may be discreet, but not deceptive toward its operators or owners.

3. Permitted Use Cases

AAM may be used for:

Internal enterprise secure communications

Journalistic field coordination

NGO or humanitarian operations

Diplomatic or corporate risk operations

Security training, red-team, or tabletop exercises

Academic or educational demonstrations

All permitted use cases assume organizational authorization.

4. Prohibited Use Cases

AAM must not be designed, marketed, or knowingly used for:

Criminal activity facilitation

Organized crime coordination

Terrorist activity

Human trafficking

Drug trafficking

Financial fraud

Sanctions evasion

Covert surveillance of individuals

Deployment without device owner consent

The system must not include features that primarily enable these uses.

5. Lawful Access & Compliance
5.1 Lawful Requests

AAM must be architected such that:

It does not intentionally obstruct lawful court orders

It does not falsely claim inability to comply

It does not destroy data outside defined retention policies

At the same time:

It does not retain unnecessary data “just in case”

It does not provide privileged backdoors

Compliance is achieved through data minimization, not exceptional access.

5.2 Jurisdictional Awareness

Deployment must account for local laws governing:

Encryption

Data retention

Cross-border data transfer

Operators are responsible for jurisdictional review

AAM does not attempt to bypass export controls or encryption regulations

6. User Consent & Transparency

AAM must ensure:

Users are aware the application includes secure communications functionality

Users are not misled about:

Data retention

Message expiration

Audit capabilities

The system is not hidden from:

Device owners

Employers

Platform administrators (where applicable)

Discretion ≠ deception.

7. Platform & Ecosystem Compliance

AAM must:

Comply with OS platform security models

Respect app store policies (if distributed via stores)

Avoid undocumented APIs or private system hooks

Avoid behavior intended to evade platform review

8. Ethical Boundaries in Design

The system must not:

Encourage risky user behavior through UI or copy

Gamify secrecy or concealment

Create false expectations of invulnerability

Frame itself as “untraceable” or “undetectable”

Language matters and must be neutral and factual.

9. AI Agent Enforcement Rules

All AI agents working on AAM must:

Treat this document as non-negotiable

Reject feature requests that violate prohibited use cases

Avoid “technically legal but ethically questionable” implementations

Escalate ambiguous scenarios for human review

Silence or omission is not consent.

10. Precedence

In case of conflict, precedence is:

Legal & Ethical Constraints (this document)

Non-Goals & Prohibited Behaviors

Threat Model

PRD

Functional Specification

Implementation details

11. Summary Statement

Abiqua Asset Management is designed to provide secure, controlled communications for legitimate organizational use, without deception, evasion, or facilitation of harm.

End of Legal & Ethical Constraints Specification