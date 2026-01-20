Product Requirements Document (PRD)
Project Name

Abiqua Asset Management (AAM)

Document Version

1.0

Status

Frozen

1. Problem Statement

Organizations operating in high-risk, high-sensitivity environments require secure communications that:

Minimize data exposure

Enforce strict lifecycle controls

Reduce human error

Avoid attracting undue attention during casual inspection

Existing consumer or enterprise messaging platforms prioritize usability and scale over operational control and deniability.

AAM addresses this gap.

2. Target Users
Primary Users

Field operators

Journalists in hostile regions

NGO and humanitarian coordinators

Internal red teams and security exercises

Secondary Users

Controllers / coordinators

Security administrators

Compliance auditors (metadata only)

3. Goals

Secure, private communication

Explicit lifecycle control of access and data

Minimal metadata exposure

Neutral, enterprise-style user experience

Deterministic, auditable behavior without content access

4. Non-Goals (High Importance)

AAM is not intended to:

Provide anonymity guarantees

Evade lawful court orders

Conceal functionality from device owners

Circumvent OS or platform safeguards

Enable criminal activity

Act as a consumer messaging replacement

5. Core Functional Capabilities

One-to-one secure messaging

Small group messaging (explicitly defined limits)

Message expiration

Device-bound identity

Explicit provisioning and decommissioning

Remote access revocation

6. Success Metrics

Zero plaintext message persistence on servers

Deterministic message deletion behavior

Successful device revocation within defined SLA

No sensitive data present in logs

UX indistinguishable from neutral enterprise tooling

7. Constraints

Must operate within applicable laws

Must use vetted cryptographic libraries

Must support audit without content access

Must avoid reliance on third-party analytics

8. Risks
Risk	Mitigation
User error	UX constraints
Device loss	Remote revocation
Insider misuse	Role separation
Infra breach	Zero-trust design
9. Open Questions (To Be Resolved Later)

Group size limits

Retention window defaults

Platform targets (iOS, Android, web)

(These will be locked before implementation.)

End of PRD