Asset #17 — Repo & Coding Standards
Project: Abiqua Asset Management (AAM)
Document Version: 1.0
Status: Frozen
1. Purpose

This document defines all coding and repository standards for Abiqua:

Repo structure

Naming conventions

Code formatting

Branching and commit conventions

Rules for Cursor-assisted development

It ensures all code is deterministic, maintainable, and auditable.

2. Repository Structure
/abiqua
├─ specs/                 # All frozen specifications (PRD, UX, ADRs, etc.)
├─ src/
│   ├─ client/            # Operator device app code
│   ├─ backend/           # Backend relay and controller interfaces
│   ├─ shared/            # Shared utilities, types, constants
├─ tests/                 # Unit and integration tests
├─ scripts/               # Build, deployment, and CI scripts
├─ docs/                  # Optional additional documentation
├─ README.md
└─ .gitignore


Notes:

All specs are versioned in specs/

Source code is divided by platform and responsibility

Cursor prompts or AI-generated code must reside in src/ or scripts/ only

3. Branching & Commits

Main branches:

main → production-ready code

develop → integration branch for feature testing

Feature branches: feature/<short-description>

Hotfix branches: hotfix/<short-description>

Commit messages: must be deterministic, present tense, reference ADR or spec ID if relevant

Example: Add message expiration enforcement (StateMachine-07)

4. Naming Conventions
Element	Convention
Variables	snake_case (Python), camelCase (JS/TS/Swift)
Constants	UPPER_SNAKE_CASE
Classes	PascalCase
Functions / Methods	Verb-based, descriptive (send_message, provision_device)
Files	Lowercase, hyphen-separated (device_lifecycle.py)
Directories	Lowercase, hyphen-separated (backend/)
5. Code Formatting

Python: PEP8-compliant

JavaScript / TypeScript: Prettier defaults

Swift: SwiftLint rules, Apple style guide

Markdown / Specs: 2-space indentation, fenced code blocks, Mermaid diagrams where appropriate

6. AI / Cursor Coding Rules

Cursor may generate code only within frozen specs and ADR constraints

All generated code must be deterministic, reproducible, and explicitly reference spec ID or ADR ID

No assumptions outside frozen UX, State Machines, or Data Classification rules

Cursor outputs must be reviewed by a human before merge

7. Testing & Coverage

Unit tests for all critical functionality

Integration tests for messaging, provisioning, revocation, and expiration flows

Code coverage: 80% minimum for critical modules (messaging, identity, state machines)

Test naming: <module>_<function>_<scenario>

8. Documentation

Inline docstrings / comments must reference relevant spec or ADR

No sensitive content in comments

All diagrams, flows, and state references must use Mermaid

9. CI / CD Rules

All PRs must pass tests before merging

Linting and formatting checks mandatory

No direct commits to main; use PRs

10. Summary Statement

The Abiqua repo and coding standards ensure deterministic, auditable, and maintainable code, whether developed by humans or AI agents.
Cursor or developers may not deviate from these standards.

End of Repo & Coding Standards Specification