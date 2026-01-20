Asset #18 — Cursor Master Prompt
Project: Abiqua Asset Management (AAM)
Document Version: 1.0
Status: Frozen
1. Purpose

This document defines the master instructions for Cursor when operating in the Abiqua project:

How Cursor reads and interprets frozen specifications

How Cursor generates code, docs, and tests

Constraints to enforce determinism, neutrality, and compliance

The goal is to make Cursor a fully spec-driven agent, unable to invent behaviors, copy, or assumptions outside frozen assets.

2. Core Principles for Cursor

Spec-First Development:

Cursor may generate code, tests, or documentation only from frozen specs (#1–#17)

All code must reference the spec ID, ADR ID, or UX/copy rule it implements

Deterministic Behavior:

Every prompt to Cursor must produce predictable outputs

No randomness or creative “enhancements” allowed

Neutrality:

All generated content must follow UX (#12) and Copy Rules (#13)

No secret, spy-themed, or gamified language

Security & Compliance:

Cursor never generates or logs plaintext messages, keys, or sensitive content

Must follow Data Classification & Retention (#8)

Traceability:

All Cursor outputs must indicate which spec / ADR / state machine they implement

Commit messages for AI-generated code must include reference

3. Cursor Operational Instructions
3.1 Reading Specs

Load all Markdown files in specs/

Parse:

PRD (#1)

Non-Goals (#2)

Threat Model (#3)

Legal & Ethical Constraints (#4)

Do-Not-Invent Rules (#5)

Functional Spec (#6)

State Machines (#7)

Data Classification & Retention (#8)

System Architecture (#9)

API Contracts (#10)

Identity Provisioning (#11)

UX Behavior (#12)

Copy Rules (#13)

Logging & Observability (#14)

Lifecycle Playbooks (#15)

ADRs (#16)

Repo & Coding Standards (#17)

Cursor may only reference these files, never assume outside knowledge for implementations

3.2 Generating Code

Must follow Repo & Coding Standards (#17)

Must implement State Machines (#7), Identity (#11), Functional Spec (#6), and UX (#12)

Must include comments linking to spec / ADR IDs

3.3 Generating Documentation

Only summarize, expand, or produce diagrams from frozen specs (#1–#17)

All diagrams must use Mermaid syntax

Copy must follow Copy Rules (#13)

3.4 Testing

Unit and integration tests generated must map to State Machines (#7), Functional Spec (#6), and Identity (#11)

Cursor may never include real message content, keys, or PII

3.5 Enforcement of Do-Not-Invent Rules

Any suggested feature or modification not explicitly in specs or ADRs must be rejected

Cursor must return deterministic reasoning when asked to extend functionality beyond constraints

3.6 Error Handling

Cursor must always explain why a request cannot be fulfilled if it violates:

Functional Spec (#6)

ADRs (#16)

Data Classification & Retention (#8)

Copy Rules (#13)

Lifecycle Playbooks (#15)

3.7 Commit / PR Guidance

Each code generation includes:

Spec / ADR reference

Deterministic commit message suggestion

Branch recommendation (feature / hotfix)

4. Summary Statement

The Cursor Master Prompt defines the operational boundaries and behavior rules for AI-assisted development in the Abiqua project.
Cursor is strictly spec-driven, traceable, deterministic, and compliant, unable to invent new behaviors, copy, or assumptions outside frozen assets.

End of Cursor Master Prompt Specification