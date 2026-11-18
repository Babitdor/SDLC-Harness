# Constraints Register — Propulsion and Machinery Control System

Document: CON-NAV-020
Revision: B

## Performance Constraints

| ID | Constraint | Value | Condition |
|---|---|---|---|
| C-PERF-01 | Sustained speed | ≥ 28 knots | Sea state 4, full-load displacement |
| C-PERF-02 | Emergency generator start | ≤ 45 s to rated speed and voltage | Cold start, 0 °C ambient |
| C-PERF-03 | Bus voltage regulation | ±5 % of nominal | All load conditions, steady-state |
| C-PERF-04 | Propulsion control response | ≤ 2 s throttle-to-power | Bridge throttle command to shaft power change |
| C-PERF-05 | Sensor data bus capacity | ≥ 500 data points | 1 Hz refresh rate, < 100 ms latency |
| C-PERF-06 | Ambient temperature range | −10 °C to +50 °C | All equipment, continuous operation |
| C-PERF-07 | Single-point failure survivability | No loss of > 50 % propulsion or total electrical loss | Any single component or cable fault |

## Physical Constraints

| ID | Constraint | Value | Notes |
|---|---|---|---|
| C-PHYS-01 | Machinery compartment footprint | ≤ 450 m² | Main engine room + auxiliary machinery space |
| C-PHYS-02 | Total system mass | ≤ 120 t | Including generators, switchboards, cabling, consoles |
| C-PHYS-03 | ECR console dimensions | ≤ 2.4 m wide × 1.2 m deep | Accommodates 2 operators seated |
| C-PHYS-04 | Cable routing | Separate port/starboard trunks | No single hit shall sever both propulsion and control |

## Budget & Schedule Constraints

| ID | Constraint | Value | Notes |
|---|---|---|---|
| C-COST-01 | Total system procurement cost | ≤ $18.5 M USD | FY2025 baseline, includes spares and training |
| C-COST-02 | Integration & test cost | ≤ $3.2 M USD | Harbour acceptance trials + sea trials |
| C-SCHED-01 | System design complete | Month 14 from contract award | PDR at M6, CDR at M12 |
| C-SCHED-02 | First-of-class installation complete | Month 28 | Dockside integration complete |
| C-SCHED-03 | Acceptance trials complete | Month 34 | Ready for fleet introduction |

## Safety Constraints

| ID | Constraint | Value | Notes |
|---|---|---|---|
| C-SAFE-01 | Emergency shutdown sequence | ≤ 30 s from detection | Collision, fire, or gas detection triggers auto-shutdown |
| C-SAFE-02 | Fire suppression activation | ≤ 10 s in machinery spaces | CO₂ or water-mist, automatic with manual override |
| C-SAFE-03 | Bilge system capacity | ≥ 110 % of largest compartment flood rate | Per damage stability analysis |
