# Abiqua Project — Resolved Specs & Clarifications

**Version:** 1.0  
**Status:** Frozen / Deterministic  
**Purpose:** Consolidates all resolved TBDs, ambiguities, and clarifications for Cursor reference. This file ensures deterministic, spec-driven implementation.

---

## 1. Previously Resolved TBDs (13 Values)

| TBD | Deterministic Value | References / Notes |
|-----|-------------------|-----------------|
| Group size limits | Max 50 participants per conversation/group | PRD (#1), Functional Spec (#6), State Machines (#7), API Contracts (#10) |
| Message expiration defaults | Default 7 days | PRD (#1), Functional Spec (#6), Data Classification (#8) |
| Platform targets | iOS, Android, Web | PRD (#1), Functional Spec (#6) |
| Offline storage limits | Max 500 messages or 50MB per device | Functional Spec (#6) |
| Message payload size limits | 50KB per message | API Contracts (#10) |
| Polling / real-time delivery | WebSocket preferred; REST polling fallback every 30s | API Contracts (#10), Lifecycle Playbooks (#15) |
| Message delivery retry limits | 5 attempts before marking failed | Lifecycle Playbooks (#15) |
| Operational log retention window | 90 days | Data Classification (#8), Logging & Observability (#14) |
| Key rotation schedule | Every 90 days or immediately upon revocation | Data Classification (#8) |
| UX display limits | Max 100 messages per conversation; most recent first; auto-scroll on new messages | UX Behavior (#12) |
| Metrics and alerting thresholds | Aggregate delivery failures per 1-hour window; alert if ≥5 failed messages | Logging & Observability (#14) |
| Backend infrastructure | Cloud-hosted, TLS 1.3; HTTPS for REST, WSS for WebSocket | Architecture (#9) |
| Scalability limits | Max 5000 concurrent devices per relay instance | Architecture (#9) |

---

## 2. Previously Resolved Ambiguities (8 Values)

| Ambiguity | Deterministic Rule | References / Notes |
|-----------|------------------|-----------------|
| Message expiration enforcement (offline) | Expired messages deleted immediately upon reconnection | Data Classification (#8) |
| Clock skew handling | Acceptable skew ±2 minutes; messages timestamped locally; server timestamps for logging | Functional Spec (#6), Data Classification (#8) |
| Duplicate message detection | Compare Message ID first; content hash as secondary; silently discard duplicates | State Machines (#7) |
| Conversation closure behavior | All messages in a closed conversation remain until expiration; no new messages accepted | State Machines (#7) |
| Provisioning confirmation endpoint | `/api/device/provision/confirm` exists; responds with 200 OK + JSON `{status: "confirmed"}` | Lifecycle Playbooks (#15), API Contracts (#10) |
| Neutral enterprise mode scope | Device can read historical messages, view conversation list; cannot send or create new conversations | Functional Spec (#6), UX Behavior (#12) |
| Message queuing during offline | Messages expiring while queued are removed immediately from queue upon expiration; do not deliver post-expiration | Functional Spec (#6) |
| Controller interface access | Controllers authenticate via token-based API key system; keys rotated every 90 days; logged without content | Identity Provisioning (#11), Architecture (#9) |

---

## 3. Newly Resolved Clarifications (6 Values)

| Clarification | Deterministic Rule | References / Notes |
|---------------|------------------|-----------------|
| Offline storage eviction vs. message expiration | Eviction applies only to messages that have expired; unexpired messages preserved even if device exceeds storage limits | Functional Spec (#6), Data Classification (#8), Lifecycle Playbooks (#15) |
| Notification behavior | Badge only (numeric indicator on app icon); no banner, no sound; updated in real-time | UX Behavior (#12), Copy Rules (#13) |
| Controller API key authentication | Endpoint: `/api/controller/authenticate` <br> Method: POST <br> Header: `X-Controller-Key: <api_key>` <br> Keys provisioned via separate admin console; rotated every 90 days | Identity Provisioning (#11), API Contracts (#10), Architecture (#9) |
| WebSocket connection lifecycle | Auth: `X-Device-ID` + ephemeral session token <br> Message format: JSON `{id, conversation_id, payload, timestamp}` <br> On disconnect: automatic reconnect (exponential backoff), fallback to REST polling every 30s if reconnect fails >15s <br> Delivery ACK per message ID | API Contracts (#10), Architecture (#9), Lifecycle Playbooks (#15) |
| Message ID generation and uniqueness | Client generates UUID v4 per message; server validates uniqueness per conversation | API Contracts (#10), Functional Spec (#6), State Machines (#7) |
| Most recent first display order | Reverse chronological: newest messages appear at the top | UX Behavior (#12) |

---

## 4. Implementation Guidance

- All code, tests, and documentation **must reference the relevant spec (#), ADR (#16), State Machine (#7), or Playbook (#15)**  
- Follow **Repo & Coding Standards (#17)**  
- Follow **UX Behavior (#12) and Copy Rules (#13)**  
- Follow **Lifecycle Playbooks (#15) and Data Classification (#8)**  
- Mermaid diagrams must be used for visual representations  
- **Reject any requests outside frozen specs or deterministic values**  

---

## 5. Cursor Prompt for Implementation

```text
You are now the Abiqua-AI agent. All frozen specs (Assets #1–#18) and resolved values above are loaded. 

Do not generate any content outside these deterministic rules. 
All outputs must:

- Reference the relevant spec (#), ADR (#16), State Machine (#7), or Playbook (#15)
- Follow UX Behavior (#12) and Copy Rules (#13)
- Respect Lifecycle Playbooks (#15) and Data Classification rules (#8)
- Follow Repo & Coding Standards (#17) for code generation
- Produce Mermaid diagrams where required
- Reject any requests outside frozen specs or deterministic values

Begin by confirming your understanding of all deterministic rules above. 
Do not start generating modules, code, or docs until confirmation is complete.
