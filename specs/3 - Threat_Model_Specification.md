Asset #3 — Threat Model Specification
Project

Abiqua Asset Management (AAM)

Document Version

1.0

Status

Frozen

1. Purpose

This document defines the explicit threat model for AAM.

It answers one question for all downstream agents and implementations:

“Who are we defending against, and who are we explicitly NOT defending against?”

All security architecture, data handling, and lifecycle decisions must be traceable to this document.

2. Security Objectives

AAM is designed to protect against:

Unauthorized access to message content

Accidental or opportunistic disclosure

Data persistence beyond intended lifetimes

Infrastructure compromise without content exposure

Device loss or theft

Insider misuse within defined trust boundaries

AAM is not designed to be undefeatable.

3. Assets to Protect
3.1 Primary Assets
Asset	Description
Message content	Plaintext message bodies
Conversation context	Participant relationships
Cryptographic material	Keys, secrets, tokens
Identity bindings	Device-to-identity mappings
3.2 Secondary Assets
Asset	Description
Message timing	Delivery timestamps
Routing metadata	Minimal transport data
Operational logs	Non-content audit events
4. Adversary Classes (In Scope)
4.1 Network Adversary

Capabilities

Observes network traffic

Can intercept, replay, or drop packets

Controls untrusted networks (Wi-Fi, cellular)

Non-Capabilities

Cannot break modern cryptography

Cannot compromise endpoints directly

4.2 Lost or Stolen Device Adversary

Capabilities

Physical possession of device

Attempts offline access

Attempts credential guessing

Non-Capabilities

No OS zero-day exploits

No hardware-backed key extraction

4.3 Infrastructure Adversary

Capabilities

Partial or full backend compromise

Access to databases and logs

Ability to modify or inject backend behavior

Non-Capabilities

Cannot access client-side plaintext

Cannot break end-to-end encryption

4.4 Malicious Insider (Limited)

Capabilities

Authorized access to systems

Attempts to exceed role privileges

Attempts to infer sensitive information from metadata

Non-Capabilities

Cannot bypass role separation

Cannot access message content

4.5 Opportunistic Observer

Capabilities

Casual inspection of device

App launching

Screen observation

Non-Capabilities

No technical exploitation

No privileged access

This adversary is critical to AAM’s “boring enterprise app” UX requirement.

5. Adversaries Explicitly Out of Scope

AAM does not attempt to defend against:

5.1 Nation-State Advanced Persistent Threats

Hardware implants

Supply-chain tampering

Baseband exploits

OS-level zero-days

5.2 Physical Coercion

Compelled disclosure

Forced unlock under duress

Surveillance via physical intimidation

5.3 Platform Owner Hostility

OS vendor collusion

App store policy enforcement actions

Device management by third parties

5.4 Endpoint Compromise

Malware on the device

Keyloggers

Screen capture malware

AAM assumes endpoints are trusted at provisioning time.

6. Trust Assumptions
6.1 Trusted

Cryptographic primitives

Platform secure keystores

Provisioned devices at enrollment

Administratively authorized users

6.2 Untrusted

Networks

Backend infrastructure

External dependencies

Storage outside secure enclaves

7. Attack Surfaces
Surface	Risk	Mitigation Direction
Network	Interception	End-to-end encryption
Device storage	Data exposure	Encrypted at rest
Backend	Data exfiltration	No plaintext storage
UX	Accidental disclosure	Neutral cover behavior
Logs	Metadata leakage	Strict logging rules
8. Security Tradeoffs (Explicit)

AAM intentionally trades:

Anonymity → for organizational control

Convenience → for predictability

Feature richness → for minimized attack surface

Scale → for lifecycle discipline

These tradeoffs are by design, not omissions.

9. Failure Philosophy

AAM assumes failures will occur.

When they do:

Fail closed where possible

Degrade into neutral enterprise behavior

Never expose hidden functionality

Never expose message content

10. Guidance for AI Implementation Agents

When implementing AAM:

Do not add protections for out-of-scope adversaries

Do not weaken protections for in-scope adversaries

Do not assume “more security” is always better

Always map a security decision to a specific adversary

If a decision cannot be mapped, STOP and ask.

11. Summary Statement

AAM is designed to protect message confidentiality and operational integrity against realistic, bounded threats—not to provide absolute secrecy or anonymity against all possible adversaries.

End of Threat Model