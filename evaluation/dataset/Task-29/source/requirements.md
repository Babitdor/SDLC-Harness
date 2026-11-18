# Requirements Specification — DC Fast-Charging Network with V2G

Document: SPEC-EVN-029
Revision: B
Status: Released for architecture
Scope: A privately funded network of public DC fast-charging sites in North
America. Each site has bidirectional chargers, a transformer, a grid connection
and a site controller, and is managed by a central charging-station management
system (CSMS) that also takes part in utility demand-response programmes.

---

## 1. Applicable Standards

| Reference | Title | Applies to |
|---|---|---|
| SAE J1772 (CCS1) | Electric vehicle conductive charge coupler — Combined Charging System | DC connector |
| SAE J3400 (NACS) | North American Charging System connector | DC connector |
| ISO 15118-20 | Road vehicles — Vehicle to grid communication interface, 2nd generation | Bidirectional power transfer, Plug & Charge |
| OCPP 2.1 (IEC 63584-210) | Open Charge Point Protocol | Charger-to-CSMS, bidirectional control |
| OpenADR 3.0 | Open Automated Demand Response | Utility demand-response signals |
| IEEE 1547-2018 / UL 1741 SB | DER interconnection / inverter certification | Export to grid during V2G |
| UL 2202 | Electric vehicle charging system equipment | Charger safety |

---

## 2. Functional Requirements

**REQ-001 — Connectors**
Each DC charging port shall provide a CCS1 connector and a SAE J3400 connector.
*Verification:* Inspection — dispenser configuration.

**REQ-002 — Site load balancing**
The site controller shall allocate power among active sessions so that total site
demand never exceeds the site power limit.
*Verification:* Test — eight simultaneous sessions requesting full power.

**REQ-003 — Authorisation**
The system shall authorise a session through the mobile app and through ISO 15118
Plug & Charge.
*Verification:* Test — each method end to end.

**REQ-004 — Billing**
The system shall bill each session per kWh delivered, net of any energy exported by
the vehicle.
*Verification:* Test — import-only and bidirectional sessions against a reference meter.

**REQ-005 — Bidirectional transfer**
The system shall export energy from a consenting vehicle to the grid when
dispatched, without discharging the vehicle below its owner's minimum state of charge.
*Verification:* Test — V2G dispatch with an ISO 15118-20 vehicle.

**REQ-006 — Demand response**
The system shall reduce or pause charging, or begin export, within 60 s of an
OpenADR event from the utility.
*Verification:* Test — OpenADR test event.

**REQ-007 — Scheduled charging**
The system shall let users schedule a session to start at a chosen time.
*Verification:* Demonstration.

**REQ-008 — Remote monitoring**
The CSMS shall show each charger's status and faults in real time and log
performance data.
*Verification:* Demonstration — dashboard with an injected fault.

**REQ-009 — Emergency shutdown**
Each site shall provide emergency stop buttons that stop all charging and isolate
the chargers from the grid.
*Verification:* Test — button actuation and isolation check.

---

## 3. Non-Functional Requirements

**REQ-NF-001 — Port uptime**
Each charging port shall achieve an average annual uptime above 97 %.
*Verification:* Analysis — CSMS availability records.

**REQ-NF-002 — Transaction time**
A receipt shall be available within 2 s of session end.
*Verification:* Test — timing over 1,000 sessions.

**REQ-NF-003 — Network capacity**
The CSMS shall support at least 50 concurrent sessions across the network.
*Verification:* Test — load test.

**REQ-NF-004 — Data protection**
Payment and personal data shall be encrypted in transit and at rest with AES-256.
*Verification:* Inspection — security architecture review.

---

## 4. Constraints

| ID | Constraint | Value | Traces to |
|---|---|---|---|
| C1 | Maximum site power | 500 kW | REQ-002 |
| C2 | Charger unit footprint | ≤ 3 m × 2 m | — |
| C3 | Operating temperature | −20 °C to +50 °C | — |
| C4 | Ports per site | 8 | REQ-002 |
| C5 | Demand-response response time | ≤ 60 s | REQ-006 |
| C6 | Charger-to-CSMS protocol | OCPP 2.1 | REQ-005 |

---

## 5. Open Points

- The 97 % uptime target is taken from the US NEVI rules (23 CFR 680) as a benchmark.
  The network is privately funded; NEVI eligibility would additionally require at
  least four ports delivering 150 kW simultaneously (600 kW, above the 500 kW site
  limit) and contactless card payment with a phone or SMS option.
- The V2G export limit per site has not been agreed with the utility.
