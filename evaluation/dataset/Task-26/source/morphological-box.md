# Morphological Box — UAV Surveillance System

Document: MB-UAS-026
Status: Concept selected

## 1. Function / Option Matrix

| Function | Option A | Option B | Option C |
|---|---|---|---|
| Propulsion / airframe | Electric ducted fan | Quadrotor | Fixed-wing |
| Navigation | GPS + IMU | Visual SLAM | Hybrid (GPS + IMU + vision) |
| Payload | EO/IR gimbal | Multispectral camera | Synthetic aperture radar |
| Communications | LTE cellular | S-band radio | Mesh network |
| Ground control | Fixed console | Portable tablet | Web dashboard |

## 2. Option Characteristics

**Airframe — quadrotor.** Hovers and tracks slowly moving targets; vertical
take-off from the GCS pad; endurance limited to roughly 40–55 minutes on batteries.
**Fixed-wing.** Endurance of several hours; cannot hover, needs a launcher or
runway and a recovery area. **Ducted fan.** Compact and guarded rotors; lowest
efficiency, shortest endurance.

**Navigation — GPS + IMU.** Proven and light; degrades near tall structures.
**Visual SLAM.** GPS-independent; degrades at night and over featureless ground.

**Payload — EO/IR gimbal.** Day and night imaging; supports object tracking.
**Synthetic aperture radar.** Imaging through cloud and darkness; forms its
aperture from platform motion.

**Communications — S-band radio.** Dedicated link, predictable range to ~10 km
line of sight. **LTE.** Coverage-dependent; cellular networks are not planned for
airborne users. **Mesh.** Range grows with node count; needs relay infrastructure.

## 3. Known Incompatibilities

- Synthetic aperture radar requires forward platform motion to form its aperture;
  it is incompatible with a hovering quadrotor or ducted fan used for loiter.
- A fixed-wing airframe cannot hover, so it cannot keep a tracked target centred
  at low speed (REQ-008) or land in the GCS maintenance bay without a runway.
- Visual SLAM alone cannot meet night operation with the EO camera.

## 4. Selected Concept

| Function | Selected | Reason |
|---|---|---|
| Airframe | Quadrotor | Hover-and-track (REQ-008); vertical recovery at the GCS |
| Navigation | GPS + IMU | Open industrial site, low complexity |
| Payload | EO/IR gimbal | Day/night imaging (REQ-007) |
| Communications | S-band radio | 10 km dedicated link (REQ-NF-003) |
| Ground control | Portable tablet | Field deployment with the GCS trailer |

The selected airframe cannot reach 2 hours on one battery; REQ-002 meets the
mission duration through battery swaps.
