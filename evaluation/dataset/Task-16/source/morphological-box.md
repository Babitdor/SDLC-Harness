# Morphological Box — Automotive ADAS

Document: MB-ADAS-016
Status: For evaluation — no option selected

| Function | Option 1 | Option 2 | Option 3 |
|---|---|---|---|
| **Perception** | Camera + Radar fusion (mono-vision, 77 GHz radar) | Camera + Radar + LiDAR fusion (stereo-vision, 4D imaging radar, 905 nm LiDAR) | Infrastructure-to-vehicle (I2V) augmented perception |
| **Localisation** | GPS + IMU + wheel-odometry (consumer-grade GNSS, 6-DOF IMU) | RTK-GNSS + IMU + HD-map matching (lane-level accuracy < 10 cm) | Visual SLAM + GPS fallback |
| **Planning** | Rule-based trajectory planner (polynomial spiral, constant-acceleration) | Optimisation-based planner (MPC with obstacle constraints) | Learning-based planner (imitation learning with safety shields) |
| **Control** | PID longitudinal + feedforward steering | Model-predictive control (MPC) for combined lateral/longitudinal | Robust H-infinity control with gain scheduling |
| **HMI** | Instrument-cluster icons + chimes (SAE J2400) | Augmented-reality head-up display (AR-HUD) | Multi-modal (visual + haptic seat + voice prompts) |
| **Logging** | Black-box event data recorder (EDR, 30 s pre/post trigger) | Continuous ring-buffer logging (CAN, Ethernet, sensor raw data) | Cloud-offload selective logging (4G/5G V2X) |

## Option Characteristics

**Perception — camera + radar.** Mature and low-cost; weak on stationary objects and
lateral position at range. **Camera + radar + lidar.** Three independent modalities
satisfy the redundancy rule and ASIL decomposition; highest cost and compute load.
**I2V-augmented.** Only works where infrastructure is equipped.

**Localisation — GPS + IMU + odometry.** Metre-level; not lane-level. **RTK + HD
map.** Lane-level (< 10 cm); depends on correction service and map currency.
**Visual SLAM + GPS.** Map-free; sensitive to weather and lighting.

**Planning — rule-based.** Predictable and easy to verify. **MPC.** Handles
constraints explicitly; heavier compute. **Learning-based.** Strong in complex
traffic; hardest to verify for ASIL D.

**Control — PID + feedforward.** Simple, separately tuned axes. **MPC.** Coordinates
lateral and longitudinal control. **H-infinity.** Robust to model uncertainty; hard
to tune and certify.

## Known Incompatibilities

- Camera + radar leaves no redundancy after a single sensor failure. It meets the
  design rules only if the one remaining modality can carry the vehicle through the
  minimal-risk manoeuvre; this must be shown before the option is selected.
- A learning-based planner cannot currently be shown to meet ASIL D (REQ-NF-003)
  without a verified rule-based safety supervisor.
- I2V-augmented perception cannot be the primary perception on highways without
  equipped infrastructure.
- MPC for both planning and control on a 75 W fanless platform (C13) needs a
  compute budget check before it can be selected.
