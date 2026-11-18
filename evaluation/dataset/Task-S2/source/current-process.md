# Current release process (as-is)

1. Developer merges to `main`.
2. Someone SSHs to the staging VM, runs `git pull && pip install -r requirements.txt && python manage.py migrate`.
3. Manual smoke test in the browser.
4. Same again on production, usually Friday afternoon.
5. Rollback: `git checkout <previous tag>`, restart gunicorn, hope.

## Pain points logged in the last two quarters
- A migration added a NOT NULL column and the deploy failed halfway; the site was down 40 minutes.
- Secrets live in a `.env` copied by hand to each VM; nobody knows if staging matches production.
- No metrics beyond the nginx access log. The last incident was found by a customer.
- Nobody can say which commit is running where.
