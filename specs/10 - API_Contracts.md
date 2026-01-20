Asset #10 — API Contracts
Project: Abiqua Asset Management (AAM)
Document Version: 1.0
Status: Frozen
1. Purpose

This document defines all API endpoints for Abiqua, including:

Request/response schemas

HTTP method / transport details

Expected success/failure codes

Security requirements

All endpoints are constrained by:

Functional Specification (#6)

State Machines (#7)

Data Classification & Retention (#8)

No additional endpoints may be invented.

2. Principles

REST over HTTPS (or WebSocket over TLS for real-time delivery)

Encrypted payloads only; plaintext never transmitted

Device-bound identity enforced

Metadata only on backend; no plaintext storage

TBD values must be defined before implementation (e.g., max group size)

3. Endpoints
3.1 Device Provisioning
Endpoint	Method	Request	Response	Description
/api/device/provision	POST	{ device_id: string, public_key: string }	{ status: "provisioned" }	Controller provisions a device with identity and keys
3.2 Device Revocation
Endpoint	Method	Request	Response	Description
/api/device/revoke	POST	{ device_id: string }	{ status: "revoked" }	Controller revokes device; triggers secure deletion on device
3.3 Send Message
Endpoint	Method	Request	Response	Description
/api/message/send	POST	{ sender_id: string, recipients: [string], payload: string (encrypted), expiration: timestamp }	{ message_id: string, status: "queued" }	Sends encrypted message; backend stores payload temporarily for delivery
3.4 Receive Message (Polling or Push)
Endpoint	Method	Request	Response	Description
/api/message/receive	GET	{ device_id: string, last_received_id: string }	{ messages: [{ message_id, payload (encrypted), sender_id, expiration }] }	Returns encrypted messages delivered to this device
3.5 Operational Event Logging
Endpoint	Method	Request	Response	Description
/api/log/event	POST	{ device_id: string, event_type: string, timestamp: string }	{ status: "logged" }	Records content-free operational events only
4. Payload Schema Notes

Message payloads are always encrypted (Confidential)

Metadata (sender_id, recipients, timestamps) are Restricted; delete immediately after use

Audit logs are Internal; may be persisted per policy

5. Security Requirements

All requests over TLS 1.3+

Device identity included in headers: X-Device-ID

No authentication beyond device-bound identity

Backend validates identity for every request

Requests containing expired messages are rejected

6. Error Handling
Code	Description	Action
400	Invalid request	Return JSON error, no sensitive info
401	Unauthorized device	Block request, return neutral message
403	Revoked device	Block request, return neutral message
404	Resource not found	Return neutral message
500	Backend failure	Retry logic only; no plaintext exposure
7. TBD Values

Max number of recipients per message

Max payload size per message

Polling interval for receive endpoint (if using REST)

8. Summary Statement

These API contracts fully define communication between devices, backend, and controller.
No additional endpoints, payload fields, or headers may be invented.
All interactions respect encryption, state machines, and data classification rules.

End of API Contracts Specification