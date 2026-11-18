# Requirements Specification — Soil-Moisture-Based Smart Irrigation Controller

Document: SPEC-IRR-014
Revision: B
Status: Released for system modelling
Scope: A single-zone landscape irrigation controller that replaces a fixed
schedule with decisions based on soil moisture, rainfall and air temperature.
Covers the sensors, the central controller and the valve controller. Excludes
the water supply and the irrigation pipework.

---

## 1. Applicable Standards

| Reference | Title | Applies to |
|---|---|---|
| EPA WaterSense Specification for Soil Moisture-Based Irrigation Controllers (2021) | Performance criteria for SMS controllers | Irrigation threshold behaviour |
| SDI-12 v1.4 | Serial-digital interface for microprocessor-based environmental sensors | Sensor bus |
| IEC 60529 | Degrees of protection provided by enclosures (IP code) | Sensor and valve enclosures |

---

## 2. Functional Requirements

**REQ-001 — Water saving**
The system shall reduce irrigation water consumption by at least 30 % compared with
the same zone irrigated on a fixed schedule.
*Verification:* Test — side-by-side comparison with a scheduled control zone over one
irrigation season.

**REQ-002 — Moisture sampling**
The system shall sample soil moisture every 5 minutes.
*Verification:* Inspection — sensor log timestamps over 24 h.

**REQ-003 — Irrigation start threshold**
The system shall open the valve when volumetric water content falls below the
configured lower threshold.
*Verification:* Test — soil column drying to below threshold.

**REQ-004 — Irrigation stop threshold**
The system shall close the valve when volumetric water content reaches the
configured upper threshold.
*Verification:* Test — soil column wetting to threshold.

**REQ-005 — Rain suspension**
The system shall suspend irrigation for 24 h after the rain sensor detects
accumulated rainfall of at least 3 mm.
*Verification:* Test — simulated rainfall at 2 mm and 4 mm.

**REQ-006 — Freeze protection**
The system shall suspend irrigation while air temperature is below 2 °C.
*Verification:* Test — climatic chamber at 1 °C and 3 °C.

**REQ-007 — Valve command**
The central controller shall command the valve controller to open or close, and
the valve controller shall report the resulting valve state.
*Verification:* Test — command and state feedback over 100 cycles.

---

## 3. Non-Functional Requirements

**REQ-NF-001 — Moisture accuracy**
The soil moisture sensor shall measure volumetric water content from 0 to 50 % with
an accuracy of ±3 % VWC.
*Verification:* Test — gravimetric calibration in site soil.

**REQ-NF-002 — Valve response**
The valve shall reach the commanded state within 2 s of the command.
*Verification:* Test — flow-meter trace.

**REQ-NF-003 — Enclosure protection**
Buried and exposed sensors shall achieve IP67.
*Verification:* Inspection — IEC 60529 test certificate.

**REQ-NF-004 — Operating temperature**
The controller shall operate from −10 °C to +50 °C.
*Verification:* Test — climatic chamber.

---

## 4. Components

| Component | Function | Interface |
|---|---|---|
| SoilMoistureSensor | Measures volumetric water content at root depth | SDI-12 |
| RainSensor | Detects accumulated rainfall ≥ 3 mm | Dry contact |
| TemperatureSensor | Measures ambient air temperature | SDI-12 |
| CentralController | Evaluates sensor data and decides irrigation | SDI-12 master; valve command output |
| ValveController | Drives a 24 V AC solenoid valve and reports its state | 24 V AC output; state feedback |

---

## 5. Constraints

| ID | Constraint | Value | Traces to |
|---|---|---|---|
| C1 | Moisture sampling interval | 5 min | REQ-002 |
| C2 | Default lower VWC threshold | 20 % | REQ-003 |
| C3 | Default upper VWC threshold | 30 % | REQ-004 |
| C4 | Rain suspension trigger / duration | ≥ 3 mm / 24 h | REQ-005 |
| C5 | Freeze lockout | < 2 °C | REQ-006 |
| C6 | Valve supply | 24 V AC solenoid | REQ-007 |

---

## 6. Open Points

- The default thresholds suit loam; thresholds for other soil types are not given.
- Whether the controller also uses a weather forecast is not decided.
