Asset #7 — State Machines
Project: Abiqua Asset Management (AAM)
Document Version: 1.0
Status: Frozen
1. Purpose

This document defines all state machines for AAM.

It translates the Functional Specification into deterministic lifecycles that Cursor or other AI agents can implement without assumptions.

All transitions, triggers, and actions are explicit. Any missing piece is TBD and blocks implementation.

2. Device Lifecycle State Machine
State	Trigger	Action	Next State
Unprovisioned	Device enrolled	Register device, generate identity	Provisioned
Provisioned	User launches app	Authenticate device identity	Active
Active	Device revoked by admin	Delete secure data, disable messaging	Revoked
Active	Device lost/stolen reported	Same as revoked	Revoked
Revoked	Device factory reset	None	Unprovisioned

Notes:

Identity is strictly device-bound.

Devices cannot skip states.

Revoked devices can only return to Unprovisioned via factory reset.

3. Message Lifecycle State Machine
State	Trigger	Action	Next State
Created	Operator sends message	Encrypt payload, assign metadata	PendingDelivery
PendingDelivery	Backend relay receives message	Store encrypted payload temporarily	Delivered / Failed
Delivered	Recipient device receives message	Decrypt locally, store securely	Active
Active	Expiration timestamp reached	Delete local message, remove from UI	Expired
Failed	Delivery retry exceeds expiration	Discard payload	Expired

Notes:

Expired messages are irrecoverable.

Duplicate messages are discarded silently.

4. Conversation Lifecycle State Machine
State	Trigger	Action	Next State
Uncreated	Operator initiates conversation	Create conversation object, assign participants	Active
Active	All participants leave or revoked	Delete conversation object	Closed
Active	Participant revoked	Remove participant	Active

Notes:

Conversation creation is explicit, no auto-discovery.

Closed conversations cannot be resurrected.

5. Provisioning & Decommissioning Lifecycle
State	Trigger	Action	Next State
Pending	Controller initiates provisioning	Send provisioning data to device	Provisioned
Provisioned	Device confirms setup	Activate device identity	Active
Active	Controller revokes device	Trigger Device Lifecycle revocation	Revoked

Notes:

Only Controllers can move devices between Pending → Provisioned → Active → Revoked.

Operators cannot self-provision or self-decommission.

6. Failure & Recovery Lifecycle
State	Trigger	Action	Next State
Normal	Network failure	Queue messages locally	Normal
Normal	Message expiration reached during network outage	Delete expired messages	Normal
Normal	Backend unreachable	Retry delivery within expiration window	Normal
Normal	Device clock skew detected	Use local time; continue expiration enforcement	Normal

Notes:

Failures do not expose errors to users beyond neutral messaging.

System remains deterministic under all edge cases.

7. Expiration Timer State Machine (per message)
State	Trigger	Action	Next State
Active	Message created	Start expiration timer	Active
Active	Timer expires	Delete message, remove from UI	Expired
Expired	N/A	Message is gone	N/A

Notes:

Timer enforcement is device-local.

Expired messages cannot be resurrected.

8. Summary Statement

These state machines fully define all deterministic behaviors in AAM.
Any behavior not captured here does not exist.
Cursor or any AI agent must implement only these transitions.
Missing TBD values (like max group size) block implementation until resolved.

End of State Machines Spec