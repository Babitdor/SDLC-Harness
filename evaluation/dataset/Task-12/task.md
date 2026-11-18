Hi — I need you to build a SysML v2 analysis case diagram for a bridge structural analysis.

The system has two analysis cases:

**StaticLoadAnalysis**
Parameters:
- spanLength = 50 m
- designLoad = 50000 N/m
- materialYieldStrength = 250 MPa
- safetyFactor = 1.5

Constraints:
- maxStress ≤ yieldStrength / safetyFactor
- maxDeflection ≤ spanLength / 600

**DynamicLoadAnalysis**
Parameters:
- windSpeed = 45 m/s
- windPressure = 1.24 kPa
- seismicZoneFactor = 0.24
- importanceFactor = 1.2
- responseReductionFactor = 3.0
- spectralAccelerationCoefficient = 2.5

Constraints:
- windForce = windPressure × exposedArea
- seismicCoefficient = (seismicZoneFactor / 2) × (importanceFactor / responseReductionFactor) × spectralAccelerationCoefficient
- seismicBaseShear = seismicCoefficient × totalDeadLoad
- combinedStress = staticStress + dynamicStress ≤ yieldStrength / safetyFactor

Please model this as a proper SysML v2 analysis case diagram with:
- A `part def BridgeStructure` with typed attributes for the bridge properties
- `analysis def` definitions for each analysis case with subject, parameters, and constraints
- Proper imports from the SI and ScalarValues libraries
- Analysis usages (instances) for each analysis case
