I'm starting a small event-ticketing service and I need the specs before anyone writes code.

The product: organisers create events with a ticket allocation; buyers reserve seats, pay, and get a scannable ticket; door staff scan a ticket to admit one person; organisers see how many seats are left. Payments go through an external provider (Stripe). Venues are in Germany, so invoices must follow EU VAT rules.

Constraints that matter to me:
- A seat can never be sold twice, even if two buyers hit "reserve" at the same moment
- Reservation is held for 10 minutes, then released
- Peak load is 500 concurrent buyers during a launch
- Data must stay in the EU
- We ship with one engineer, so keep the first version small

Please produce the requirement set, the design documents, the API contract, the backlog and test plan, the CI setup, and the core diagrams.