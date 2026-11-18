# Constraints Register — Powertrain Assembly Cell

Document: CON-ROB-021
Revision: B

C1–C3 are stated in the requirements specification; this register continues from C4.

## Physical Constraints

| ID | Constraint | Value | Notes |
|---|---|---|---|
| C4 | Cell footprint | 8 m × 6 m (48 m²) | Includes robot base, conveyor, part bins, tool rack, operator panel |
| C5 | Maximum robot payload | 20 kg | Includes end-effector mass; derate by 30 % for high-speed moves |
| C6 | Safety-rated stop distance | ≤ 500 mm | From max axis speed; verified by simulation and physical test |
| C7 | Positioning repeatability | ±0.1 mm | At TCP after calibration; measured per ISO 9283 |
| C8 | Maximum reach | 1 800 mm | From robot base to farthest fixture point |
| C9 | Floor load capacity | 5 000 kg/m² | Industrial floor rating; no pit required |

## Performance Constraints

| ID | Constraint | Value | Notes |
|---|---|---|---|
| C10 | Production rate | 60 assemblies / hour | Sustained over 8-hour shift; includes 5 % line-down allowance |
| C11 | Overall Equipment Effectiveness (OEE) | ≥ 85 % | Availability × Performance × Quality |
| C12 | Vision false-reject rate | < 0.1 % | Per 1 000 inspected assemblies |
| C13 | Safety system response time | ≤ 100 ms | From intrusion to motion stop |
| C14 | Mean Time Between Failures (MTBF) | ≥ 2 000 hours | Cell-level (excluding consumables) |
| C15 | Mean Time To Repair (MTTR) | ≤ 30 minutes | For common faults (tool jam, vision misalignment) |

## Budget & Timeline Constraints

| ID | Constraint | Value | Notes |
|---|---|---|---|
| C16 | Capital expenditure (CAPEX) | ≤ € 350 000 | Includes robots, controllers, vision, safety, conveyor, integration |
| C17 | Engineering hours | ≤ 1 200 hours | Mechanical + electrical + software design, simulation, commissioning |
| C18 | Project timeline | 16 weeks | From kick-off to customer acceptance (FAT + SAT) |
| C19 | Training & documentation | 40 hours | Operator training + maintenance manuals + spare parts list |
