We have a Django monolith and the release process is killing us. I need a spec I can hand to the team.

Current state: one repo, three environments, releases by SSH-ing into a VM and running migrate by hand. Rollbacks are "git checkout the previous tag and hope". Two incidents last quarter traced to a migration that ran before the app was ready.

What I want documented:
- How a commit becomes a release, with the gates it must pass
- The rollback procedure, including what happens to schema changes
- How secrets are handled across the three environments
- The observability we need before we can call a deploy safe
- A migration strategy that cannot take the site down

Also write the test plan that proves the pipeline works, and the diagrams for the deploy flow.