# Morphological Box — Autonomous UAV Delivery System

Document: MB-UDS-015
Status: For evaluation — no option selected


| Function | Option 1 | Option 2 | Option 3 |
|---|---|---|---|
| **Propulsion** | Brushless DC motors + fixed-pitch propellers (quadcopter) | Coaxial contra-rotating rotors (octocopter) | Ducted fans for reduced noise |
| **Navigation** | Multi-constellation GNSS (GPS + Galileo + GLONASS) | Visual-inertial odometry (VIO) with downward-facing camera | Ultra-wideband (UWB) beacon-based localisation |
| **Obstacle Detection** | Forward-facing stereo camera + LiDAR fusion | 360° mmWave radar array | Time-of-flight (ToF) depth sensors + ultrasonic |
| **Payload Delivery** | Electromagnetic latch release (winch) | Parachute-assisted precision drop | Landing + manual retrieval by recipient |
| **Communication** | 4G/5G cellular link (command & control) | LoRaWAN telemetry + Wi-Fi video downlink | Dedicated 2.4 GHz ISM-band radio (MAVLink) |
| **Power Management** | Fixed Li-ion 12S pack, ~2.3 kWh | Li-ion pack with supercapacitor buffer for take-off peaks | Swappable Li-ion pack with automated hot-dock station |

## Option Characteristics

**Propulsion — quadcopter.** Simplest and most efficient multirotor; loss of one
motor is not survivable. **Coaxial octocopter.** Tolerates a motor failure; coaxial
rotors are less efficient than an equivalent quadcopter, so endurance is lower.
**Ducted fans.** Quieter and guarded; lowest hover efficiency.

**Navigation — multi-constellation GNSS.** Accurate in the open; degraded in urban
canyons. **VIO.** GNSS-independent near buildings; needs texture and light.
**UWB beacons.** Centimetre-level near beacons; only where beacons are installed.

**Obstacle detection — stereo + LiDAR.** Dense 3-D detection; heaviest and most
power-hungry. **mmWave radar.** Works in rain, fog and darkness; coarse angular
resolution. **ToF + ultrasonic.** Light and cheap; short range only.

**Payload delivery — winch.** Drone stays above head height; slower drop.
**Parachute drop.** Fastest; wind drift limits precision. **Landing.** Simple;
brings rotors close to people.

**Communication — 4G/5G cellular.** Wide area; coverage at altitude is not
guaranteed. **LoRaWAN + Wi-Fi.** Long-range telemetry, short-range video.
**2.4 GHz ISM radio.** Dedicated link; limited to a few kilometres in urban areas.

**Power — fixed pack.** Simplest; aircraft is idle while charging. **Supercapacitor
buffer.** Reduces peak battery current; adds mass. **Swappable pack with hot-dock.**
Minutes of turnaround; needs dock infrastructure at the depot.

## Known Incompatibilities

- UWB beacon navigation cannot be the only navigation means: drop points are not
  beacon-equipped.
- ToF + ultrasonic cannot detect obstacles at the stopping distance for 15 m/s
  cruise; they are admissible only alongside a longer-range sensor.
- A landing-based delivery conflicts with REQ-005 in drop zones where people are
  present.
- A 2.4 GHz ISM link cannot reliably hold the C2 link across a multi-kilometre
  urban service area without relays, because buildings block line of sight.
