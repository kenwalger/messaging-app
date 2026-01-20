Asset #11 — Identity Provisioning & Lifecycle
Project: Abiqua Asset Management (AAM)
Document Version: 1.0
Status: Frozen
1. Purpose

This document defines all identity-related operations for Abiqua:

Provisioning new device identities

Authenticating devices

Revoking devices

Decommissioning / recycling identities

It ensures that identity handling is deterministic, secure, and compliant with the Threat Model (#3), Legal & Ethical Constraints (#4), and Functional Spec (#6).

2. Identity Definition

Identity is device-bound; each device has exactly one identity.

Identity consists of:

device_id (unique UUID)

Public/private key pair

Provisioning metadata (enrollment timestamp, controller ID)

Identities cannot be shared or transferred between devices.

3. Provisioning Lifecycle
State	Trigger	Action	Next State
Pending	Controller initiates provisioning	Generate device_id, key pair; send encrypted provisioning payload to device	Provisioned
Provisioned	Device confirms receipt	Activate device identity; enable messaging features	Active
Active	N/A	Normal operation	Active

Notes:

Only controllers can initiate provisioning.

Device must confirm provisioning to reach Active state.

4. Authentication Behavior

On app launch:

Device presents device_id

Verifies key pair with backend

If valid → grant access

If invalid or revoked → neutral enterprise mode

No alternative login methods exist (e.g., passwords, email, MFA).

5. Revocation Lifecycle
State	Trigger	Action	Next State
Active	Controller revokes device	Mark identity revoked in backend; notify device	Revoked
Revoked	Device detects revocation	Delete local secure data; disable messaging	Revoked
Revoked	Device factory reset	Identity destroyed	Unprovisioned

Notes:

Device revocation is immediate and irreversible.

No plaintext or keys remain after revocation.

6. Device Decommissioning

Decommission occurs after revocation and/or factory reset

Identity is removed from backend provisioning DB

Device can be reused only after a new provisioning cycle

7. Edge Case Handling
Scenario	Required Behavior
Device offline during revocation	Device deletes secure data upon next interaction
Device lost/stolen	Controller revokes; device enters Revoked state remotely
Identity duplication detected	Reject provisioning; log incident; escalate to Controller
8. Security & Compliance Points

Cryptographic key generation and storage must use trusted primitives

Device authentication is mandatory for all messaging operations

Revocation must enforce immediate cessation of messaging capability

9. Summary Statement

Every Abiqua identity is device-bound, provisioned, and lifecycle-managed deterministically.
Controllers are the sole authority over identity state transitions.
Any undefined behavior does not exist.

End of Identity Provisioning & Lifecycle Specification