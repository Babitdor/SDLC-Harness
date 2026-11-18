# Library lending — known constraints

## Regulatory
- GDPR: patron records must be deletable; borrowing history is personal data.
- Public-sector procurement: no vendor lock-in for the catalogue store.

## Integration
- Consortium catalogue API: paginated, ~800 ms p95, returns partial records when a branch is offline. No SLA.
- Notifications go through the city's existing mail gateway (SMTP, rate-limited to 200/hour).

## Operational
- Two branches, one shared catalogue, ~40k patrons.
- Fines must be auditable to the cent; the finance office reconciles monthly.
- The system must work read-only when the consortium API is down (search from last synced snapshot).
