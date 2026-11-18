# Morphological Box — LEO Communications Satellite

Document: MB-SAT-022
Status: For evaluation — no option selected

| Function | Option 1 | Option 2 | Option 3 |
|---|---|---|---|
| Communication Payload | Multi-beam phased-array antenna (Ka-band, 16 beams) | Reflector antenna with beam-forming network (Ku-band) | Helical array for UHF/VHF backup link |
| Attitude Control | 3-axis reaction wheels + star tracker (0.01° accuracy) | Control-moment gyroscopes (CMG) with sun sensor | Hybrid: reaction wheels for fine pointing, thrusters for desaturation |
| Power System | Deployable triple-junction GaAs solar arrays + Li-ion battery (35 min eclipse) | Thin-film solar cells on body panels + Li-Po battery | Solar array tracking (single-axis gimbal) + NiH₂ battery |
| Thermal Management | Passive: MLI blankets + OSR radiators + heat pipes | Active: pumped-fluid loop with external radiator | Hybrid: heat pipes for payload, MLI for bus, heaters for survival |
| Propulsion | Electric propulsion (Hall-effect thruster, Xe, Isp 1600 s) | Green monopropellant (LMP-103S, Isp ≈ 250 s) | Cold-gas (N₂) for reaction-wheel desaturation only |
| Onboard Processing | Digital channeliser + FPGA-based packet switch (20 Gbps) | Software-defined radio (SDR) on multi-core LEON processor | Hybrid: ASIC for beamforming + FPGA for routing |

## Option Characteristics

**Payload — Ka-band phased array.** Electronically steered beams, many simultaneous
users; high power and thermal load. **Ku-band reflector with beam-forming network.**
Mature; fewer, less agile beams. **UHF/VHF helix.** Low-rate backup only.

**Attitude — reaction wheels + star tracker.** Fine pointing for 0.1°; wheels need
periodic desaturation. **CMGs.** Large torque for agile slewing; heavy for a 500 kg
satellite.

**Propulsion — Hall thruster (Xe, Isp ~1600 s).** Very low propellant mass for 7
years of drag make-up and disposal; low thrust. **Green monopropellant (Isp ~250 s).**
Quick collision-avoidance burns; far more propellant mass. **Cold gas.** Only for
wheel desaturation.

**Processing — channeliser + FPGA switch.** Reprogrammable, 20 Gbps class.
**SDR on LEON processors.** Flexible, radiation-tolerant; limited throughput.
**ASIC + FPGA hybrid.** Best power efficiency; ASIC fixes the beamforming design.

## Known Incompatibilities

- A UHF/VHF helix cannot deliver 20 Gbps (REQ-NF-001); it is admissible only as a
  backup link.
- Cold-gas propulsion alone cannot provide drag make-up over 7 years or end-of-life
  disposal.
- A software-defined radio on LEON processors cannot reach 20 Gbps of routing
  (REQ-NF-001).
- Body-mounted thin-film cells cannot supply 1.5 kW orbit-average (C2) within the
  stowed envelope (C3).
