---
name: secrets-management
description: Reference CI secrets by name only, declare least-privilege permissions and keep credentials out of logs in planning/CI_CD.md and planning/ci/pipeline.yml. Use whenever a pipeline file or the CI/CD design is written or repaired.
source: https://github.com/wshobson/agents/blob/main/plugins/cicd-automation/skills/secrets-management/SKILL.md
license: MIT
---

## When to use

You are @DevOps and about to write `planning/CI_CD.md` or
`planning/ci/pipeline.yml`, or a stage needs a credential to run.

## Rules

- CI_CD.md lists secret NAMES and the store each comes from. A value never
  appears in any file the agent writes — not even a placeholder that looks real.
- The workflow reads a secret as `${{ secrets.NAME }}`. Never a literal in
  `env:`, never `echo $TOKEN`, never `set -x` around a credential.
- Declare `permissions:` explicitly and start from `contents: read`. A job that
  needs more names only what it needs; no `write-all`.
- Prefer the platform token with scoped permissions (`GITHUB_TOKEN`) over a
  long-lived personal token in a repository secret.
- Scope a secret to the step that needs it, not to the whole job.
- Rotate on a schedule and on exposure. A leaked secret is revoked first, then
  replaced — the pipeline change lands after the revocation.
- Third-party actions are pinned by tag or SHA and reviewed: an action can read
  every secret handed to its step.
- A secret passed as a build argument or baked into an image is visible in image
  history — mount it at run time instead.

## Minimal worked example

```yaml
jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - name: Push image
        env:
          REGISTRY_TOKEN: ${{ secrets.REGISTRY_TOKEN }}
        run: ./scripts/push.sh
```

```
# Secrets and Permissions
- REGISTRY_TOKEN: repository secret, 90-day rotation, write scope on the registry only
- GITHUB_TOKEN: platform token, contents: read + packages: write, no rotation
```

## Common failure modes

- `env: {API_KEY: "changeme"}` committed so the pipeline "runs locally".
- `permissions: write-all` widened to make a failing step pass.
- A secret echoed by a failing command's traceback — the build log is the leak.
- CI_CD.md listing a secret's value because the schema says "where it comes
  from": that means the store, not the string.
