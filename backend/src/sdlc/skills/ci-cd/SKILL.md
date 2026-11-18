---
name: ci-cd
description: Design CI/CD stages and write the GitHub Actions workflow, validating it to zero errors with ci_pipeline_validator_tool. Use whenever planning/CI_CD.md or planning/ci/pipeline.yml is written or repaired.
license: proprietary
---

## When to use

You are @DevOps and `planning/TEST_PLAN.md` exists. The stages you design must
run the test levels that document defines.

## Rules

- GitHub Actions only: top-level `on:` and `jobs:` are both required.
- Every job declares `runs-on` and a non-empty `steps` list.
- Every step is either `uses:` or `run:` — never both, never neither.
- Stages in the workflow match the stages table in CI_CD.md, in the same order.
- Secrets are referenced as `secrets.NAME`; the value never appears in a file.
- Quote nothing you do not need to quote: `on:` is a real key here, but YAML
  1.1 parsers read it as boolean true — keep it unquoted and let the validator
  handle it.

## Minimal worked example

```yaml
name: ci
on:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Unit tests
        run: pytest -q
```

## Common failure modes

- A job with `steps: []` — accepted by YAML, rejected by the validator.
- A step with both `uses` and `run`: GitHub silently ignores one.
- Hard-coded credentials in an `env:` block.
- Stages in the pipeline that no stage in CI_CD.md mentions (or the reverse).
