# Morphological Box — Naval Surface Combatant Propulsion & Machinery Control

Document: MB-NAV-020
Status: For evaluation — no option selected

| Function | Option 1 | Option 2 | Option 3 |
|---|---|---|---|
| Propulsion | Combined diesel-electric and gas turbine (CODLAG) with cross-connect gearbox | Integrated electric drive with podded propulsors | Mechanical direct-drive gas turbine with controllable-pitch propeller |
| Power Generation | 4 × 4 MW diesel generators, 1 × 20 MW gas turbine generator | 2 × 6 MW diesel generators, 2 × 3 MW shaft generators | 3 × 5 MW MTG (marine turbine generators), 2 × 2 MW emergency DGs |
| Damage Control | Zonal electrical distribution with automatic bus-tie breakers and sectionalising | Distributed DC microgrids with fault-tolerant ring bus | Redundant port/starboard switchboards with cross-deck feeds |
| Machinery Monitoring | Centralised ECR console with dual-redundant servers and local display units | Distributed smart sensors with CANbus data concentrators and bridge repeater | Wireless mesh sensor network with handheld maintenance terminals |
| Bridge Control | Integrated throttle and manoeuvring joystick with dynamic positioning hold | Repeater panel with telegraph-style throttle and bow thruster control | Touch-screen MFD with route-planning and auto-throttle modes |
| Auxiliary Systems | Variable-speed seawater cooling pumps, electric bilge pumps, fire-main pressure-regulated | Pneumatic bilge ejectors, fixed CO₂ flooding, freshwater hydrophone tank | Dual-redundant fire main with cross-connections, air-tight compartment dampers |

## Option Characteristics

**Propulsion — CODLAG.** Quiet electric drive at low speed, gas turbine for sprint;
complex cross-connect gearbox. **Integrated electric drive with pods.** All power
through the electrical plant; pods ease manoeuvring but add shock and underwater
vulnerability. **Mechanical gas turbine with CPP.** Simplest high-speed plant;
noisy and inefficient at low speed.

**Damage control — zonal distribution with bus-tie breakers.** Isolates damage by
zone. **DC microgrids with ring bus.** Fast fault isolation; newer technology.
**Port/starboard switchboards.** Simple split; less granular isolation.

**Monitoring — centralised ECR with redundant servers.** Single point of control,
redundant hardware. **Distributed smart sensors on CAN.** Less cabling; CAN
bandwidth limits the point count. **Wireless mesh.** Least cabling; vulnerable to
jamming and EMC issues.

## Known Incompatibilities

- A wireless sensor mesh conflicts with the EMC rule requiring shielded or
  fibre-optic data buses and with MIL-STD-461 (C3).
- Port/starboard switchboards alone give two zones, fewer than the three
  damage-control zones required by the zonal electrical rule.
- A mechanical gas-turbine plant without electric drive cannot supply propulsion
  from the ship service generators, weakening the 50 % survivability rule.
- A centralised ECR without a separately routed bridge repeater conflicts with the
  cable-separation constraint (C-PHYS-04).
