# Requirements Specification — LEO Satellite Communication System

Document: SPEC-SATCOM-009
Revision: B
Status: Released for architecture partitioning
Scope: End-to-end communication system for a 500 kg low Earth orbit spacecraft:
the ground segment (antennas and data processing), the space segment power and
thermal subsystems that sustain the communication payload, and the protocols
governing frequency use and link security.

---

## 1. Applicable Standards

| Reference | Title | Applies to |
|---|---|---|
| ITU Radio Regulations | Frequency allocations and coordination | Frequency allocation |
| CCSDS 131.0-B | TM synchronization and channel coding | Downlink coding |
| CCSDS 232.0-B | TC space data link protocol | Command uplink |
| CCSDS 355.0-B | Space Data Link Security (SDLS) protocol | Link encryption and authentication |
| FIPS 140-3 | Security requirements for cryptographic modules | Cryptographic module validation |
| ECSS-E-ST-20C | Space engineering — Electrical and electronic | Power bus |
| ECSS-E-ST-31C | Space engineering — Thermal control | Thermal design |

FIPS 140-2 validations move to the NIST historical list on 22 September 2026;
new modules for this programme shall hold FIPS 140-3 validation.

---

## 2. Functional Requirements

### Ground segment

**REQ-001 — Two-way communication**
The system shall provide two-way communication between the ground stations and
the spacecraft during every visible pass.
*Verification:* Test — end-to-end command and telemetry exchange on a pass.

**REQ-002 — Antenna tracking**
The ground segment shall track the spacecraft through each pass using parabolic
reflector antennas, with phased-array antennas as secondary assets.
*Verification:* Test — tracking error logged over ten passes.

**REQ-003 — Data processing**
The ground segment shall demodulate, decode and forward telemetry, command
acknowledgements and payload data to the mission operations centre.
*Verification:* Test — end-to-end data delivery check.

**REQ-004 — Station handover**
The system shall hand over the link between ground stations as the spacecraft
passes below one station's horizon and rises above the next.
*Verification:* Demonstration — scheduled two-station pass sequence.

### Space segment

**REQ-005 — Power provision**
The space segment shall provide at least 2 kW of continuous regulated power to
all subsystems, including through eclipse.
*Verification:* Analysis — orbital power budget; test — solar array and battery
qualification.

**REQ-006 — Thermal control**
The space segment shall maintain all communication equipment between −10 °C and
+50 °C.
*Verification:* Test — thermal vacuum cycling.

### Communication protocols

**REQ-007 — Frequency allocation**
The system shall operate its links in the allocations listed in C3 to C5.
*Verification:* Inspection — ITU filing and transmitter configuration.

**REQ-008 — Command link security**
The system shall encrypt and authenticate every command uplink using AES-256 in a
FIPS 140-3 validated cryptographic module.
*Verification:* Inspection — module certificate; test — rejected unauthenticated
command.

**REQ-009 — Downlink rate**
The system shall sustain a payload downlink data rate of at least 100 Mbps.
*Verification:* Test — bit-error-rate measurement at 100 Mbps.

---

## 3. Non-Functional Requirements

**REQ-NF-001 — Link availability**
The link shall be available for at least 99.5 % of scheduled pass time.
*Verification:* Analysis — link budget with rain-fade statistics for each station.

**REQ-NF-002 — Acquisition time**
A ground station shall acquire the spacecraft within 30 s of acquisition of signal.
*Verification:* Test — acquisition timing over ten passes.

**REQ-NF-003 — Encryption latency**
Link encryption shall add no more than 5 ms of latency per frame.
*Verification:* Test — latency measurement with and without SDLS.

---

## 4. Constraints

| ID | Constraint | Value | Traces to |
|---|---|---|---|
| C1 | Spacecraft mass | ≤ 500 kg | REQ-005 |
| C2 | Ground antenna reflector diameter | ≤ 7.3 m | REQ-002 |
| C3 | UHF telemetry band | 300–1000 MHz (low-rate beacon) | REQ-007 |
| C4 | S-band TT&C | 2025–2110 MHz uplink; 2200–2290 MHz downlink | REQ-007 |
| C5 | Ka-band payload downlink | 25.5–27.0 GHz | REQ-007, REQ-009 |
| C6 | Power bus | 28 V DC ± 1 % | REQ-005 |
| C7 | Radiator area available | ≤ 2.5 m² | REQ-006 |
| C8 | Cryptographic module validation | FIPS 140-3 | REQ-008 |

---

## 5. Open Points

- The number and locations of ground stations are not fixed; handover timing in
  REQ-004 depends on them.
- The Ka-band ITU coordination is in progress; the final sub-band is not assigned.
