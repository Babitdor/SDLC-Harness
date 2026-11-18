Hi — I've attached the requirements specification for a 22 kW AC charging point
we're taking into detailed design (SPEC-EVSE-001 Rev C).

Could you put together the systems model for it? What I need is:

1. A structured requirements model derived from the specification — the spec is
   written for procurement and I want the requirements as model elements with
   IDs preserved so we can trace against them later.
2. A block definition diagram for the charging point showing the internal
   components and their key attributes with units — the controller, the supply
   contactor, the metering, the residual current protection, the pilot
   signalling electronics, the socket assembly and the communications module.

Please respect the constraints table in section 5 — the current rating, the
enclosure envelope, the 6 mA DC residual threshold, the contact temperature
limits and the standby power budget all come from the customer specification and
are not negotiable.

Use SysML v2. Model the protection functions as distinct parts rather than
folding them into the controller, since they are separately certified items.
