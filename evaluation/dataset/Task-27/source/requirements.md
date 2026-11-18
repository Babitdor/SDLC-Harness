# Requirements Specification — Smart Greenhouse Control System

Document: SPEC-GH-027
Revision: B
Status: Released for architecture
Scope: Climate, irrigation, fertigation and lighting control for a 200 m²
twin-wall polycarbonate greenhouse growing lettuce and herbs in substrate beds,
year-round, in a temperate climate (winter design outdoor temperature −5 °C).

---

## 1. Applicable Standards

| Reference | Title | Applies to |
|---|---|---|
| EN 13031-1 | Greenhouses — Design and construction — Commercial production greenhouses | Structure and loads |
| IEC 60364-7-705 | Low-voltage electrical installations — Agricultural and horticultural premises | Electrical installation |
| ANSI/ASABE S640 | Quantities and units of electromagnetic radiation for plants | PPFD and DLI definitions |
| ANSI/ASABE S642 | Measurement and testing of LED products for plant growth | Luminaire efficacy |

---

## 2. Functional Requirements

**REQ-001 — Air temperature**
The system shall hold internal air temperature between 15 °C and 30 °C.
*Verification:* Test — 30-day logged temperature including a cold spell.

**REQ-002 — Relative humidity**
The system shall hold relative humidity between 40 % and 80 %.
*Verification:* Test — 30-day logged humidity.

**REQ-003 — Irrigation**
The system shall irrigate each bed from real-time substrate moisture readings.
*Verification:* Test — bed drying to threshold and irrigation response.

**REQ-004 — CO₂ enrichment**
The system shall enrich CO₂ to between 800 and 1000 ppm during the photoperiod
while vents are closed.
*Verification:* Test — CO₂ log with vents closed and open.

**REQ-005 — Supplemental lighting**
The system shall switch grow lights to achieve a daily light integral (DLI) of at
least 17 mol·m⁻²·d⁻¹ at canopy level.
*Verification:* Test — PAR sensor integration over a low-light day.

**REQ-006 — Ventilation**
The system shall operate vent louvres and exhaust fans to remove excess heat and
humidity.
*Verification:* Test — high-radiation day response.

**REQ-007 — Nutrient dosing**
The system shall dose nutrient stock solutions into the irrigation water at
programmable ratios, holding EC within ±0.1 mS/cm of the set point.
*Verification:* Test — EC log over one week.

**REQ-008 — Monitoring dashboard**
The system shall provide a remote dashboard showing live sensor values, actuator
states and historical trends.
*Verification:* Demonstration.

**REQ-009 — Emergency shutdown**
The system shall shut down heating, lighting and dosing and open vents on detection
of fire, overheating above 40 °C or loss of control-system health.
*Verification:* Test — injected fault for each trigger.

---

## 3. Non-Functional Requirements

**REQ-NF-001 — Control loop availability**
No single component failure shall stop temperature control.
*Verification:* Analysis — FMEA of the control loop.

**REQ-NF-002 — Sensor accuracy**
Temperature sensors shall be accurate to ±0.5 °C and humidity sensors to ±2 % RH.
*Verification:* Test — calibration against a reference.

**REQ-NF-003 — Data retention**
The system shall retain sensor and actuator logs for at least 1 year.
*Verification:* Inspection — storage sizing and retention policy.

**REQ-NF-004 — Sensor scale**
The system shall support up to 60 sensor nodes.
*Verification:* Test — 60 nodes reporting concurrently.

---

## 4. Constraints

| ID | Constraint | Value | Traces to |
|---|---|---|---|
| C1 | Growing area | 200 m² | — |
| C2 | Irrigation water use | ≤ 500 L/day | REQ-003 |
| C3 | Peak electrical demand, all systems | ≤ 20 kW | REQ-001, REQ-005 |
| C4 | Lighting power density | ≤ 50 W/m² | REQ-005 |
| C5 | Winter design outdoor temperature | −5 °C | REQ-001 |

### Power budget for C3

| Consumer | Peak demand |
|---|---|
| LED grow lights (200 m² × 50 W/m²) | 10.0 kW |
| Heat pump: 22 kW heat loss (320 m² glazing × 3.5 W/m²K × 20 K), COP 3 | 7.5 kW |
| Fans, pumps, dosing, controls | 1.5 kW |
| **Total (winter night, lighting on)** | **19.0 kW** |

Lighting and peak heating coincide on winter nights, so this is the governing case.

---

## 5. Open Points

- Whether heating may be curtailed during grid peak tariffs is not decided.
- The lettuce cultivar, and so the exact DLI target, may change.
