# Requirements Specification — Hydrogen Refuelling Station (HRS)

Document: SPEC-HRS-700-002
Revision: B
Status: Issued for concept design
Site: Motorway service area, hard-standing plot 48 m × 26 m
Client: Regional mobility operator

---

## 1. Purpose and Scope

This specification covers a public gaseous hydrogen refuelling station
dispensing to light-duty fuel cell electric vehicles at 70 MPa and to captive
fleet vehicles (delivery vans, refuse collection) at 35 MPa. It covers the
hydrogen supply, compression, storage, precooling, dispensing and safety
systems, and the station control system. It excludes the vehicles, the upstream
hydrogen production and the site civil works.

---

## 2. Applicable Standards

| Reference | Title |
|---|---|
| ISO 19880-1:2020 | Gaseous hydrogen — Fuelling stations — Part 1: General requirements |
| ISO 19880-8 | Fuel quality control |
| SAE J2601 | Fueling protocols for light duty gaseous hydrogen surface vehicles |
| SAE J2799 | Hydrogen surface vehicle to station communications |
| ISO 14687 | Hydrogen fuel quality — Grade D for PEM fuel cell road vehicles |
| IEC 60079 | Explosive atmospheres — equipment and area classification |
| ATEX 2014/34/EU | Equipment for potentially explosive atmospheres |
| ISO 15916 | Basic considerations for the safety of hydrogen systems |

---

## 3. Functional Requirements

### 3.1 Dispensing

**REQ-001 — Dispensing pressure classes**
The station shall dispense gaseous hydrogen at nominal working pressure 70 MPa
(H70) to light-duty vehicles and at 35 MPa (H35) to fleet vehicles.
*Verification:* Commissioning fills at both pressure classes.

**REQ-002 — Fuelling protocol**
The station shall implement the SAE J2601 fuelling protocol, using the
communications-enabled fill where the vehicle supports SAE J2799 infrared
communication, and shall fall back to the non-communication table-based fill
otherwise.
*Verification:* Protocol conformance test with a reference vehicle and a
protocol analyser.

**REQ-003 — Precooling category**
The station shall precool dispensed hydrogen to fuel delivery temperature
category T40, that is −40 °C to −33 °C at the dispenser nozzle, for H70 fills.
*Verification:* Nozzle temperature measurement across a full fill.

**REQ-004 — Fill time**
The station shall complete a nominal H70 fill of a 5 kg vehicle tank from 10 %
to 95 % state of charge within 3 minutes under reference ambient conditions of
+20 °C.
*Verification:* Timed fills, minimum 10 consecutive.

**REQ-005 — Vehicle tank temperature limit**
The station shall control the pressure ramp rate such that the vehicle tank gas
temperature does not exceed 85 °C at any point during the fill.
*Verification:* Instrumented tank fill at worst-case ambient.

**REQ-006 — Back-to-back capability**
The station shall support at least 6 consecutive H70 fills at 5 kg each with no
more than 5 minutes recovery between fills.
*Verification:* Sequential fill test.

**REQ-007 — Dispenser count**
The station shall provide two dispensers, each with an H70 and an H35 nozzle,
capable of independent simultaneous operation.
*Verification:* Simultaneous dual-dispense test.

**REQ-008 — Metering and payment**
Each dispenser shall meter dispensed mass to a custody-transfer accuracy of
±1.5 % and shall support contactless card and fleet-account payment.
*Verification:* Mass meter calibration certificate; payment transaction test.

### 3.2 Supply, Compression and Storage

**REQ-009 — Hydrogen supply**
The station shall accept hydrogen supply from the selected supply concept and
shall not be dependent on a single delivery mode for continuity of service.
*Verification:* Design review against the selected concept.

**REQ-010 — Fuel quality**
Hydrogen delivered at the nozzle shall meet ISO 14687 Grade D, and the station
shall provide sampling provision at the dispenser for periodic quality
verification.
*Verification:* Laboratory analysis of a dispenser sample.

**REQ-011 — Compression**
The station shall compress hydrogen to the pressure required to fill the
high-pressure buffer bank, and the compressor shall be capable of the daily
throughput specified in REQ-013 with one unit out of service where redundancy is
provided by the selected concept.
*Verification:* Throughput test.

**REQ-012 — Cascade storage**
The station shall store hydrogen in a cascade of at least three pressure banks
so that vehicle filling draws sequentially from low, medium and high pressure
banks to minimise compressor duty.
*Verification:* Bank pressure logging during a fill sequence.

**REQ-013 — Daily throughput**
The station shall dispense at least 420 kg of hydrogen per 24 hours, with a peak
hourly capability of 60 kg/h.
*Verification:* 24-hour throughput demonstration.

**REQ-014 — Buffer autonomy**
Stored hydrogen shall be sufficient for at least 80 kg of dispensing with the
compressor out of service.
*Verification:* Compressor-off dispensing test.

### 3.3 Control and Monitoring

**REQ-015 — Station control system**
The station shall provide a supervisory control system that sequences
compression, bank selection, precooling and dispensing, and that logs all
process variables at not less than 1 Hz.
*Verification:* Control system factory acceptance test.

**REQ-016 — Remote monitoring**
The station shall transmit operational status, alarms and throughput data to a
remote operations centre, and shall permit remote shutdown but not remote start
of dispensing.
*Verification:* Remote interface test.

**REQ-017 — Leak detection**
The station shall monitor for hydrogen leakage in every enclosed process
compartment and shall initiate an automatic shutdown on detection of a
concentration exceeding 25 % of the lower flammability limit.
*Verification:* Calibrated gas injection test.

**REQ-018 — Emergency shutdown**
The station shall provide manual emergency shutdown actuators at each dispenser
and at the site entrance, and activation shall isolate the hydrogen supply and
vent to a safe location within 10 seconds.
*Verification:* ESD actuation timing test.

---

## 4. Safety Requirements

**REQ-019 — Hazardous area classification**
The station shall be designed with hazardous area classification per IEC 60079,
and all equipment within a classified zone shall be certified for that zone
under ATEX.
*Verification:* Area classification drawing and equipment certificate review.

**REQ-020 — Separation distances**
The station layout shall maintain the separation distances derived from the
site-specific risk assessment between hydrogen process equipment, the dispensing
area, the site boundary, occupied buildings and the public highway.
*Verification:* Layout review against the risk assessment.

**REQ-021 — Venting**
The station shall vent hydrogen through dedicated vent stacks discharging
vertically upward at a height and location determined by dispersion analysis,
and vent outlets shall not discharge toward occupied areas.
*Verification:* Dispersion analysis and as-built survey.

**REQ-022 — Fire detection**
The station shall provide flame detection covering the compression, storage and
dispensing areas, interlocked to emergency shutdown.
*Verification:* Flame source response test.

**REQ-023 — Overpressure protection**
Every pressure-containing system shall be protected by a pressure relief device
sized for the credible worst-case overpressure and discharging to the vent
system.
*Verification:* Relief sizing calculation review.

**REQ-024 — Crash protection**
Dispensers and exposed process equipment within the vehicle circulation area
shall be protected against vehicle impact.
*Verification:* Inspection against the layout drawing.

---

## 5. Non-Functional Requirements

**REQ-NF-001 — Site envelope**
All station equipment, including safety separation, shall fit within the
48 m × 26 m hard-standing plot.

**REQ-NF-002 — Availability**
The station shall achieve 97 % availability measured monthly, excluding planned
maintenance.

**REQ-NF-003 — Noise**
Station noise shall not exceed 55 dB(A) at the site boundary during normal
operation.

**REQ-NF-004 — Energy consumption**
Specific energy consumption for compression and precooling shall not exceed
4.0 kWh per kilogram dispensed, averaged over a representative week.

**REQ-NF-005 — Vehicle circulation**
The layout shall permit forward-in, forward-out circulation for a 12 m rigid
vehicle without reversing.

**REQ-NF-006 — Maintenance access**
Compression and precooling skids shall be removable without disturbing the
storage banks or the dispensing island.

**REQ-NF-007 — Service life**
Design life shall be 20 years for static equipment and 10 years for rotating
equipment.

---

## 6. Open Points

The following are not resolved in this revision and are to be closed during
concept selection:

- Hydrogen supply mode is not selected. Options are under evaluation in the
  attached morphological box.
- Compression technology is not selected.
- Whether precooling is centralised or per-dispenser is not selected.
- The site-specific separation distances are subject to the risk assessment,
  which is not yet complete. The layout must therefore be produced with the
  separation distances as parameters, not as fixed values.
