# Morphological Box — Automated Robotic Assembly Cell

Document: MB-ROB-021
Status: For evaluation — no option selected

| Function | Technology Option 1 | Technology Option 2 | Technology Option 3 |
|---|---|---|---|
| Part handling | Vacuum gripper (suction cup array, 0–20 kg) | Magnetic gripper (electro-permanent, ferrous parts) | Mechanical gripper (parallel jaw, servo-controlled) |
| Fastening | Electric screwdriver (torque-controlled, ±3 % accuracy) | Pneumatic nutrunner (high-speed, torque + angle) | — |
| Inspection | 2D machine vision (area-scan camera, LED ring light) | 3D laser profilometer (line scanner, sub-mm resolution) | — |
| Tool changing | Automatic tool changer (ISO 9409-1 flange, pneumatic lock) | Manual quick-change adapter (operator-assisted, keyed) | — |
| Conveyor control | Variable-frequency drive (VFD) with encoder feedback | On/off motor with photo-eye part detection | — |
| Safety monitoring | Laser area scanner (SICK microScan3, 270° field) | Light curtain (safety-rated, Type 4, 14 mm resolution) | Safety mat (pressure-sensitive, zone-based) |

## Option Characteristics

**Part handling — vacuum.** Fast, handles smooth flat surfaces; poor on cast or
porous surfaces and oily parts. **Magnetic.** Strong hold on ferrous parts; no use
for aluminium housings. **Mechanical parallel jaw.** Positive grip on any material;
needs part-specific fingers.

**Fastening — electric screwdriver.** Torque and angle control with traceable data,
low noise. **Pneumatic nutrunner.** Fast and high torque; torque/angle monitoring
needs added transducers.

**Inspection — 2D vision.** Presence and in-plane alignment; misses height errors.
**3D profilometer.** Measures height and seating; slower, needs part motion under
the line.

**Safety — laser area scanner.** Configurable protective and warning fields around
the whole cell. **Light curtain.** Protects openings; does not detect a person
already inside. **Safety mat.** Detects presence on the floor; wear-prone.

## Known Incompatibilities

- Magnetic grippers cannot handle aluminium powertrain housings.
- A pneumatic nutrunner without torque and angle transducers cannot satisfy
  REQ-003 or the traceability log (REQ-009).
- Light curtains alone cannot detect a person remaining inside the envelope, so they
  cannot support the restart condition in REQ-007 without additional presence
  sensing.
- 2D vision checks in-plane alignment only; a part that is present but not fully
  seated would pass REQ-004 unless seating is checked another way.
