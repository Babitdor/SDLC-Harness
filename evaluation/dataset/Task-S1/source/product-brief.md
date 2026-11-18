# Event ticketing — product brief v0.3

## Actors
- Organiser — creates events, allocates seats, cancels events
- Buyer — reserves and pays for seats
- Door staff — scans tickets at the venue
- Payment provider — Stripe (external, webhooks for settlement)

## Known requirements from the founder
1. Seat inventory must be exact: no overselling under concurrent reservation.
2. Reservations expire after 10 minutes if unpaid.
3. Refunds within 14 days of purchase are mandatory (EU consumer law).
4. Invoices must carry EU VAT lines and a sequential invoice number.
5. Data residency: EU only.
6. Launch target: 500 concurrent buyers, 20 events live at once.
7. Door scanning must work offline and reconcile when back online.
8. One engineer maintains this, so no bespoke infrastructure.

## Out of scope for v1
- Seat maps / picking a specific seat
- Multi-currency
- Native mobile apps
