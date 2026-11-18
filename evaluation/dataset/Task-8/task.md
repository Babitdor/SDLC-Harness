We need a SysML v2 parametric diagram for our hydraulic braking system performance analysis. The requirements are in the attached file.

Build a parametric model with the following constraint blocks:

1. **BrakingForceEquation**: F = P × A × μ (braking force = hydraulic pressure × piston area × friction coefficient)
2. **StoppingDistanceEquation**: d = v² / 2a (stopping distance = initial velocity squared / 2 × deceleration)
3. **DecelerationEquation**: a = F / m (deceleration = braking force / vehicle mass)

Then create a **BrakingPerformanceConstraint** that composes all three equations and verifies:
- Minimum braking force ≥ **12,000 N**
- Maximum stopping distance ≤ **40 m**
- From an initial velocity of **25 m/s**
- With vehicle mass **1500 kg**

Use proper SysML v2 patterns:
- `public import ScalarValues::*; public import ISQ::*; public import SI::*;`
- Typed parameters with SI units (Pa, m², N, kg, m/s, m/s², m)
- A `part def HydraulicBrakingSystem` with attributes that map to constraint parameters
- A concrete `part` usage with nominal design values and constraint bindings

The requirements doc has the full set of performance targets and design constraints — make sure the parametric model traces to them.