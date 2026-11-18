I need an API design review package for a public library-lending API, before we build it.

Scope: patrons search the catalogue, place a hold on a book that is checked out, and get notified when it is available. Librarians manage copies and loan periods. A national consortium shares the catalogue with us, so the book records come from an external service we don't control.

Things I already know I care about:
- Patrons are identified by a library card number, and we must not leak which books a person has borrowed
- Holds must be fair: first placed, first served, across branches
- The consortium feed is slow and occasionally returns partial records
- Loans have due dates, renewals, and overdue fines in cents
- GDPR: patron data must be deletable on request

Give me the data model, the API contract, the user stories with acceptance criteria, and the diagrams that show a hold being placed and fulfilled.