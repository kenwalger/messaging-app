Asset #15 — Lifecycle Playbooks
Project: Abiqua Asset Management (AAM)
Document Version: 1.0
Status: Frozen
1. Purpose

This document defines all operational playbooks for Abiqua, including:

Device provisioning

Device revocation

Device decommissioning

Recovery from offline or failed states

Playbooks are deterministic, neutral, and step-by-step, ensuring any operator or AI agent can execute them without ambiguity.

2. Device Provisioning Playbook

Objective: Create a new device identity and enable messaging.

Steps:

Controller initiates provisioning via /api/device/provision

Backend generates device_id and key pair

Encrypted provisioning payload sent to device

Device receives payload, stores keys in secure keystore

Device confirms provisioning via /api/device/provision/confirm

Backend updates Device Lifecycle state to Active

UI displays: “Device successfully provisioned”

State Machine Mapping:

Pending → Provisioned → Active

3. Device Revocation Playbook

Objective: Immediately disable a device and erase secure data.

Steps:

Controller sends /api/device/revoke with device_id

Backend marks identity as Revoked

Device receives revocation notice

Device deletes all secure local data (messages, keys)

Messaging features disabled in UI → display “Messaging Disabled”

State Machine Mapping:

Active → Revoked

4. Device Decommissioning Playbook

Objective: Safely retire a device for reuse or disposal.

Steps:

Ensure device is in Revoked state

Controller confirms deletion of device identity in backend

Device factory reset (optional for reuse)

Device may be re-provisioned as a new identity

State Machine Mapping:

Revoked → Unprovisioned

5. Message Lifecycle Playbook

Objective: Ensure deterministic message delivery, expiration, and cleanup.

Steps:

Operator composes message → sends /api/message/send

Backend queues message for delivery (metadata only)

Recipient device receives encrypted payload → decrypts locally

Expiration timer starts immediately

Upon expiration, message is deleted locally → removed from conversation UI

Edge Cases:

Device offline → process message upon next connection

Message delivery fails → retry until expiration

Expired message → delete silently

State Machine Mapping:

Created → PendingDelivery → Delivered → Active → Expired

6. Recovery / Offline Playbook

Objective: Maintain deterministic behavior in network failures.

Steps:

Device offline → queue outgoing messages locally

Poll backend periodically (or via WebSocket) for pending messages

Expired messages removed from queue without user intervention

Apply any missed state transitions (revocation, provisioning updates) once online

State Machine Mapping:

All offline behaviors map to existing State Machines (Device & Message Lifecycle)

7. Playbook Formatting & Enforcement

Steps are numbered, linear, and deterministic

Each step maps to a State Machine transition

UI copy and feedback must follow Copy Rules (#13)

No step may reference sensitive content directly (messages, keys)

8. TBD Values

Polling interval for offline recovery

Maximum retries for message delivery

Optional factory reset procedures for decommissioned devices

9. Summary Statement

Lifecycle Playbooks define all operational steps for provisioning, revocation, decommissioning, messaging, and recovery.
Cursor or operators must follow these exactly.
Any behavior not described here does not exist.

End of Lifecycle Playbooks Specification