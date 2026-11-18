# Domain Knowledge Base — LEO Communications Satellite

## Applicable Standards

- **ECSS-E-ST-10C** — Space engineering: System engineering general requirements
- **ECSS-E-ST-20C** — Space engineering: Electrical and electronic
- **ECSS-E-ST-50C** — Space engineering: Communications
- **ECSS-Q-ST-70C** — Space product assurance: Materials, mechanical parts and processes
- **CCSDS 131.0-B** — TM Synchronization and Channel Coding
- **CCSDS 133.0-B** — Space Packet Protocol
- **CCSDS 732.0-B** — AOS Space Data Link Protocol
- **ITU Radio Regulations, Article 22** — Limits (EPFD) protecting geostationary systems from non-geostationary FSS systems
- **ISO 24113** — Space systems — Space debris mitigation requirements

## Design Rules

- **Radiation Hardening (RHA)**: Total ionising dose (TID) tolerance ≥ 50 krad(Si) for 7-year LEO mission. Use radiation-hardened parts (e.g. LEON3-FT processor) or shielding (≥ 3 mm Al equivalent) for sensitive electronics. Single-event upset (SEU) rate < 1×10⁻⁵ errors/bit/day.
- **Orbital Debris Mitigation**: Comply with ISO 24113 and ECSS-U-AS-10C. Passivate propulsion system at end of life. Dispose of each satellite within 5 years of end of mission, as the FCC has required of US-licensed LEO satellites since 2022; at 550 km natural decay supports this. Collision avoidance manoeuvre capability for conjunction probability > 1×10⁻⁴.
- **Reliability**: Design for 0.85 probability of success over 7 years (ECSS-Q-ST-30C). Redundancy on all critical functions (power bus, attitude control, comms chain). No single-point failure shall cause loss of mission.
- **EMC/EMI**: ECSS-E-ST-20-07C. Radiated emissions below ITU-R masks. Self-compatibility: transmitter out-of-band emissions shall not desensitise the receiver (frequency separation ≥ 10 % of bandwidth).
