# Technology Knowledge Base — Hydrogen Refuelling

Document: KB-HRS-002
Purpose: Background reference for concept selection. Descriptive only — nothing
in this document is a requirement.

---

## 1. Why Precooling Is Necessary

Filling a vehicle tank from a higher-pressure source is close to adiabatic. The
gas entering the tank is compressed by the gas already there, and the work done
on it appears as a temperature rise. For a 70 MPa fill completed in a few
minutes, an uncooled fill would drive the tank gas well past the 85 °C limit that
Type IV composite tanks are qualified to.

Two levers control the peak temperature: the temperature of the gas delivered at
the nozzle, and the rate at which pressure is ramped. Colder delivery permits a
faster ramp for the same peak temperature. SAE J2601 formalises this by defining
fuel delivery temperature categories — T40 (−40 °C to −33 °C), T30 (−33 °C to
−26 °C) and T20 (−26 °C to −17.5 °C) — and by publishing, for each category and
each vehicle tank volume band, the pressure ramp rate that keeps the tank within
limits.

A T40 station can achieve the three-minute reference fill. A T30 or T20 station
cannot, and must either extend the fill or terminate at a lower state of charge.
This is why precooling capacity, not compression capacity, is usually what
determines whether a station meets its fill-time target.

The protocol has two variants. In the communications fill, the vehicle reports
its tank temperature, pressure and capacity over an infrared link (SAE J2799),
and the station adjusts the ramp accordingly, typically reaching 95–100 % state
of charge. In the non-communication fill the station has no vehicle data and must
use a conservative table indexed by ambient temperature and starting pressure,
which generally ends at a lower state of charge.

---

## 2. The Cascade Principle

A vehicle tank is filled by pressure difference. If every fill drew from a single
950 bar bank, the whole mass transferred would have to be raised to 950 bar by the
compressor, and the bank would be drawn down across its full pressure range on
each fill.

A cascade divides storage into banks at different pressures — commonly around
450, 650 and 950 bar. The fill begins on the low bank, which equalises against
the near-empty vehicle tank; when the flow falls off, the station switches to the
medium bank, and finally to the high bank for the last pressure rise. Only the
final portion of the mass is taken from the most expensive storage.

The consequences are: less compressor work per kilogram dispensed, better
back-to-back fill performance because the low and medium banks recover quickly,
and more vessels and a more complex bank-selection control. The control logic
must decide switch points, and poor switch points waste either time or
compressor duty.

---

## 3. Compression Technologies

**Diaphragm compressors** use hydraulic fluid to flex a stack of metal diaphragms
against the gas. Because the gas is separated from the hydraulic side by the
diaphragm stack, there is no dynamic seal in the gas path: leakage is negligible
and the gas is not contaminated by lubricant. This makes them the common choice
in refuelling service where ISO 14687 purity must be preserved. They are proven
above 900 bar. Diaphragms are a consumable and their replacement is a planned
maintenance activity; a diaphragm failure is detected by monitoring the interlayer
cavity.

**Ionic liquid compressors** replace the solid piston with a column of ionic
liquid driven hydraulically. There is no piston ring and therefore no sliding
seal against the gas. The liquid also absorbs heat of compression, giving a
near-isothermal process and good efficiency. The technology has fewer moving
parts than a reciprocating machine but a smaller installed base and a narrower
service network.

**Reciprocating piston compressors** are the conventional machine: a piston in a
cylinder with rings sealing against the bore. They are mechanically simple, well
understood and widely serviceable. The sliding seal is both a small leakage path
and a route for lubricant to reach the gas, so downstream purification may be
required to hold Grade D purity.

**Electrochemical compressors** pump hydrogen across a proton-exchange membrane
under an applied potential. They have no moving parts and are silent and
efficient, but available flow rates and pressures remain below what a public
refuelling station requires.

---

## 4. Supply Modes

**Tube trailer delivery** brings hydrogen as compressed gas at around 300 bar on
a trailer that is parked and connected at the station. Capital cost is low and
the station can be commissioned quickly, but the delivered mass per trailer is
modest, so at a throughput of a few hundred kilograms per day deliveries are
frequent, and the station needs a trailer standing area and a connection panel.
Station availability becomes partly a logistics question.

**Liquid hydrogen delivery** carries far more mass per vehicle movement, because
liquid hydrogen is roughly an order of magnitude denser than 300 bar gas. The
station stores it cryogenically and vaporises it on demand, or pumps it as a
liquid and vaporises at pressure, which avoids a gas compressor altogether.
The costs are a cryogenic hazard class on site, boil-off losses when throughput
is low relative to storage, and more specialised maintenance.

**On-site electrolysis** produces hydrogen from water and electricity at the
station, removing delivery logistics and enabling a genuinely green fuel where
the electricity is renewable. It requires a substantial electrical connection,
water treatment, and a significant footprint, and it shifts the station's
operating cost onto the electricity tariff.

---

## 5. Hazardous Areas and Separation

Hydrogen is buoyant, has a wide flammability range and a very low ignition
energy. Station safety design therefore concentrates on preventing accumulation,
ensuring any release disperses upward and away, and keeping ignition sources out
of areas where a flammable mixture could exist.

Areas around potential release points are classified into zones by the likelihood
of a flammable atmosphere being present, and equipment installed in a zone must
be certified for it. Separation distances between process equipment, the
dispensing area, the site boundary, occupied buildings and the public highway are
derived from a site-specific risk assessment considering credible release
scenarios and their consequences.

The 2020 edition of ISO 19880-1 removed the tabulated safety distances that
appeared in the earlier technical specification, in favour of the risk-assessment
approach. In practice this means a station layout cannot be finalised from the
standard alone: the separation distances are an output of the site risk
assessment, and a layout produced before that assessment completes should treat
them as parameters.

---

## 6. Where Station Energy Goes

Specific energy consumption is usually quoted in kWh per kilogram dispensed and
is dominated by two consumers.

Compression is the larger. The work required depends on the pressure ratio, and
therefore on the storage concept: a cascade reduces the average ratio compared to
filling everything to the top bank pressure.

Precooling is the second, and unlike compression it scales with utilisation in an
awkward way. A chiller must hold the heat transfer fluid cold whether or not
vehicles arrive, so a station at low utilisation spends a disproportionate
fraction of its energy keeping the precooler ready. Thermal storage and
per-dispenser cooling are both attempts to improve this, by decoupling
refrigeration capacity from instantaneous demand or by shortening the cold path
that must be maintained.
