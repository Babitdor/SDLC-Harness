# Requirements Specification — Active Medical Cold-Chain Container

Document: SPEC-CC-030
Revision: B
Status: Released for architecture
Scope: A portable, compressor-cooled transport container for vaccine vials,
powered from the delivery vehicle or mains with an internal battery backup, with
temperature logging, cellular alerting and inventory scanning. Covers one
container; excludes the fleet management back-end.

---

## 1. Applicable Standards and Guidelines

| Reference | Title | Applies to |
|---|---|---|
| WHO PQS E003 | Refrigerators and freezers — performance specifications and test procedures | Active cooling performance |
| WHO PQS E006 | Temperature monitoring devices | Logger and alarm |
| EU GDP (2013/C 343/01) | Guidelines on Good Distribution Practice of medicinal products | Temperature-controlled transport |
| UN 38.3 | UN Manual of Tests and Criteria — lithium battery transport tests | Backup battery |
| IEC 60529 | Degrees of protection (IP code) | Enclosure |

---

## 2. Functional Requirements

**REQ-001 — Storage temperature**
The container shall hold its payload between 2 °C and 8 °C for a 48-hour mission at
ambient temperatures up to 43 °C while supplied with external power.
*Verification:* Test — 48 h climatic chamber run at 43 °C, WHO PQS E003 method.

**REQ-002 — Temperature logging**
The container shall log payload temperature at intervals of no more than 5 minutes
with a timestamp.
*Verification:* Inspection — log after a 48 h run.

**REQ-003 — Location capture**
The container shall record GPS position at mission start and at every temperature
deviation.
*Verification:* Test — induced deviation during a road trial.

**REQ-004 — Tamper evidence**
The container shall show visibly if the lid has been opened during transit.
*Verification:* Inspection — seal state after opening.

**REQ-005 — Shock recording**
The container shall record every shock event above 5 g peak.
*Verification:* Test — drop table at 4 g and 6 g.

**REQ-006 — Remote alert**
The container shall send a cellular alert within 60 s of payload temperature
leaving 2–8 °C.
*Verification:* Test — induced deviation with network trace.

**REQ-007 — Vial capacity**
The container shall hold at least 200 standard 5 mL vials in a removable tray.
*Verification:* Inspection — loaded tray.

**REQ-008 — Inventory scanning**
The container shall scan vial barcodes on loading and unloading and log each scan.
*Verification:* Test — load and unload 200 vials.

**REQ-009 — Defrost**
The container shall defrost its evaporator automatically without the payload
leaving 2–8 °C.
*Verification:* Test — payload temperature through a defrost cycle.

---

## 3. Non-Functional Requirements

**REQ-NF-001 — Sensor accuracy**
The payload temperature sensor shall be accurate to ±0.5 °C from −10 °C to +50 °C.
*Verification:* Test — calibration against a reference thermometer.

**REQ-NF-002 — Local alarm**
The container shall raise an audible and visual alarm within 60 s of payload
temperature leaving 2–8 °C.
*Verification:* Test — induced deviation.

**REQ-NF-003 — Data retention**
The container shall retain temperature, GPS, shock and event data for at least
90 days.
*Verification:* Inspection — storage sizing.

**REQ-NF-004 — Battery backup**
On loss of external power the container shall maintain full cooling and monitoring
for at least 4 hours at 43 °C ambient.
*Verification:* Test — external power removed in the climatic chamber.

---

## 4. Constraints

| ID | Constraint | Value | Traces to |
|---|---|---|---|
| C1 | Loaded mass (vials, tray, battery, container) | ≤ 30 kg | — |
| C2 | External dimensions | ≤ 60 × 40 × 40 cm | REQ-007 |
| C3 | Backup battery energy per pack | ≤ 100 Wh | REQ-NF-004 |
| C4 | External supply | 12/24 V DC vehicle or 100–240 V AC mains | REQ-001 |
| C5 | Payload temperature band | 2–8 °C | REQ-001 |

### Energy check for REQ-NF-004 and C3

Surface area 1.28 m² × effective vacuum-panel U-value 0.35 W/m²K × ΔT 38 K gives a
heat leak of about 17 W. At a compressor COP of 1.5 that is about 11 W, plus about
5 W for fans and electronics: roughly 16 W, or 64 Wh for 4 hours — within one
100 Wh pack.

---

## 5. Open Points

- How long the container holds 2–8 °C passively after the backup battery is
  exhausted is not specified.
- Whether the container will travel as air freight, which brings IATA
  dangerous-goods handling for the battery, is not decided.
