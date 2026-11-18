# Requirements Specification — AC Charging Point (Mode 3, 22 kW)

Document: SPEC-EVSE-001
Revision: C
Status: Released for design
Scope: Wall-mounted / pedestal AC charging point for semi-public car parks
(workplace, hotel, retail). Single charging point, one Type 2 socket-outlet.

---

## 1. Applicable Standards

| Reference | Title | Applies to |
|---|---|---|
| IEC 61851-1:2019 | EV conductive charging system — General requirements | Control pilot, modes, safety |
| IEC 61851-21-2 | EMC requirements for off-board EV chargers | Emissions/immunity |
| IEC 62196-2 | Plugs, socket-outlets — Type 2 | Connector interface |
| IEC 62955 | Residual direct current detecting device (RDC-DD) | DC fault detection |
| OCPP 2.0.1 | Open Charge Point Protocol | Backend communication |
| Directive 2014/32/EU (MID) | Measuring Instruments Directive | Billing metering |
| ISO 15118-2 | V2G communication interface | Optional smart charging |

---

## 2. Functional Requirements

**REQ-001 — Charging mode**
The charging point shall implement Mode 3 conductive AC charging in accordance
with IEC 61851-1.
*Verification:* Type test per IEC 61851-1 clause 6.

**REQ-002 — Connector**
The charging point shall provide one Type 2 socket-outlet per IEC 62196-2,
rated 32 A three-phase.
*Verification:* Inspection and dimensional check.

**REQ-003 — Rated output**
The charging point shall deliver up to 22 kW (400 V AC, 3-phase, 32 A) and
shall support reduced single-phase operation at 7.4 kW (230 V, 32 A).
*Verification:* Power measurement at rated load.

**REQ-004 — Control pilot signalling**
The charging point shall generate a 1 kHz ±0.5 % PWM control pilot signal at
±12 V and shall encode the available current in the duty cycle such that for
duty cycle D in the range 10 % < D ≤ 85 %, available current = D × 0.6 A.
*Verification:* Oscilloscope measurement across the full duty-cycle range.

**REQ-005 — Pilot state detection**
The charging point shall detect and correctly transition between control pilot
states A (not connected, +12 V), B (connected, not ready, +9 V), C (connected,
ready to charge, +6 V) and shall interrupt energy transfer within 100 ms of an
unexpected transition to state A or E.
*Verification:* State-machine test with an EV simulator.

**REQ-006 — Proximity pilot**
The charging point shall read the proximity pilot resistance to determine cable
current-carrying capacity and shall limit the advertised current to the lower of
the cable rating and the installation rating.
*Verification:* Test with 13 A, 20 A and 32 A rated cables.

**REQ-007 — Authorisation**
The charging point shall authorise a charging session by ISO/IEC 14443 RFID
card, by remote backend authorisation, or by free-vend configuration.
*Verification:* Functional test of all three paths.

**REQ-008 — Energy metering**
The charging point shall measure delivered energy with an MID-compliant meter of
accuracy class B or better and shall record energy per session.
*Verification:* Meter conformity certificate and end-to-end session check.

**REQ-009 — Backend communication**
The charging point shall communicate with a central system using OCPP 2.0.1 over
a secure WebSocket connection, and shall support the BootNotification,
StatusNotification, Authorize, TransactionEvent and MeterValues messages.
*Verification:* OCPP compliance test suite.

**REQ-010 — Offline operation**
The charging point shall continue to authorise sessions from a locally cached
authorisation list when the backend connection is unavailable, and shall queue
transaction records for transmission on reconnection.
*Verification:* Network-interruption test of at least 24 h.

**REQ-011 — Load management**
The charging point shall accept a current setpoint from the backend or from a
local load-management controller and shall adjust the advertised current within
5 s of receiving it.
*Verification:* Setpoint step-response measurement.

**REQ-012 — Socket locking**
The charging point shall lock the connector for the duration of energy transfer
and shall release the lock on session termination or on loss of supply.
*Verification:* Mechanical actuation test, 10,000 cycles.

**REQ-013 — User interface**
The charging point shall indicate the operational state (available, occupied,
charging, fault) by a visible indicator readable at 5 m in direct sunlight.
*Verification:* Photometric measurement and field inspection.

---

## 3. Protection and Safety Requirements

**REQ-014 — Residual current protection**
The charging point shall provide residual current protection comprising an
RCD type A together with a residual DC detection function that interrupts
supply at a smooth DC residual current of 6 mA per IEC 62955.
*Verification:* Injection test per IEC 62955.

**REQ-015 — Protective earth monitoring**
The charging point shall verify protective earth continuity before closing the
supply contactor and shall not energise the socket if PE integrity is not
confirmed.
*Verification:* PE-open fault injection.

**REQ-016 — Overcurrent and welded-contact detection**
The charging point shall detect a welded supply contactor and shall enter a
locked-out fault state, requiring manual reset, on detection.
*Verification:* Fault injection with a shorted contactor.

**REQ-017 — Temperature monitoring**
The charging point shall monitor socket-outlet contact temperature and shall
derate charging current when contact temperature exceeds 70 °C, interrupting
supply at 90 °C.
*Verification:* Thermal test at rated current.

---

## 4. Non-Functional Requirements

**REQ-NF-001 — Ingress and impact protection**
The enclosure shall achieve IP54 and IK08 as installed.
*Verification:* Type test per IEC 60529 / IEC 62262.

**REQ-NF-002 — Operating environment**
The charging point shall operate over −25 °C to +45 °C ambient at up to 95 %
relative humidity, non-condensing.
*Verification:* Climatic chamber test.

**REQ-NF-003 — Standby power**
Standby power consumption shall not exceed 5 W with the backend connection
established and no vehicle connected.
*Verification:* Power measurement over a 1 h idle window.

**REQ-NF-004 — Availability**
The charging point shall achieve an operational availability of at least 99 % on
a monthly basis, excluding scheduled maintenance and upstream supply outages.
*Verification:* Field data over a 3-month pilot.

**REQ-NF-005 — Firmware update**
The charging point shall support signed over-the-air firmware update initiated
from the backend, and shall roll back automatically on a failed update.
*Verification:* Update and forced-failure test.

**REQ-NF-006 — Service access**
Field-replaceable units — contactor, RCD module, controller board, meter —
shall be replaceable without removing the enclosure from its mounting.
*Verification:* Maintenance demonstration.

---

## 5. Constraints

| ID | Constraint | Value |
|---|---|---|
| C1 | Maximum continuous output current | 32 A per phase |
| C2 | Nominal supply | 400 V AC ±10 %, 50 Hz, TN-S |
| C3 | Maximum enclosure envelope | 400 × 300 × 180 mm |
| C4 | Maximum mass, wall-mounted | 12 kg |
| C5 | DC residual current trip threshold | 6 mA |
| C6 | Contact temperature derate / trip | 70 °C / 90 °C |
| C7 | Standby power budget | 5 W |
| C8 | Cable length, tethered variant | 5 m maximum |
