# Morphological Box — Autonomous Mobile Robot

Document: MB-AMR-028
Status: Concept selected

## 1. Function / Option Matrix

| Function | Option A | Option B | Option C |
|---|---|---|---|
| Locomotion | Differential drive | Mecanum drive | Tracked drive |
| Navigation | Laser SLAM | Visual SLAM | Magnetic tape following |
| Payload handling | Flat deck | Roller conveyor | Lifting fork |
| Battery | LiFePO₄ | Lead-acid | Supercapacitor |
| Safety | Safety laser scanner + bumper | Vision + ultrasonic | All four combined |

## 2. Option Characteristics

**Locomotion — differential drive.** Simple, robust, turns on the spot; cannot move
sideways. **Mecanum.** Omnidirectional; sensitive to floor debris, lower load
capacity and higher wheel wear. **Tracked.** High traction; marks and wears
warehouse floors, inefficient.

**Navigation — laser SLAM.** Map-based, re-plans around obstacles, no floor
installation. **Visual SLAM.** Low-cost sensors; sensitive to lighting changes.
**Magnetic tape.** Very reliable path; fixed routes, re-layout requires re-taping,
and the robot can only stop at an obstacle, not detour.

**Payload — lifting fork.** Engages loads at rack and workstation height directly.
**Flat deck.** Needs manual or external transfer. **Roller conveyor.** Needs powered
conveyor at every station.

**Battery — LiFePO₄.** Opportunity charging, long cycle life, stable chemistry.
**Lead-acid.** Heavy, no opportunity charging, maintenance. **Supercapacitor.**
Very fast charging, but minutes of runtime.

**Safety — laser scanner + bumper.** Safety-rated scanners are available to PL d;
the bumper is a last-resort contact detector. **Vision + ultrasonic.** Not
available as safety-rated personnel detection.

## 3. Known Incompatibilities

- A supercapacitor store cannot meet 8 hours of operation (REQ-NF-001).
- Magnetic tape following cannot re-plan around obstacles (REQ-002).
- Vision + ultrasonic alone cannot provide PL d personnel detection
  (REQ-NF-006) under ISO 3691-4.
- A flat deck cannot engage loads at rack height (REQ-006).

## 4. Selected Concept

| Function | Selected | Reason |
|---|---|---|
| Locomotion | Differential drive | Robust on warehouse floors, on-the-spot turning |
| Navigation | Laser SLAM | Re-planning around obstacles (REQ-002) |
| Payload | Lifting fork | Rack and workstation engagement (REQ-006) |
| Battery | LiFePO₄ | 8 h endurance with opportunity charging |
| Safety | Laser scanner + bumper | PL d personnel detection (REQ-NF-006) |
