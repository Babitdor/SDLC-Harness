---
name: test-strategy
description: Turn acceptance criteria into a test plan whose cases close every criterion, choosing unit/integration/contract/e2e levels and writing Gherkin that parses. Use whenever planning/TEST_PLAN.md is written or audited.
license: proprietary
---

## When to use

You are @Planning and `requirements/ACCEPTANCE_CRITERIA.md` exists. Each
AC-NNN must map to at least one TC-NNN, or be listed as a coverage gap.

## Rules

- Pick the lowest level that can observe the outcome: unit for pure logic,
  integration for persistence, contract for an OpenAPI endpoint, e2e only for
  a cross-service journey.
- Every TC names the AC it verifies (`Verifies: AC-NNN`).
- Gherkin, when used, needs `Feature:` and at least one `Scenario:` — the
  parser rejects a stray `Given` outside a scenario.
- Uncovered criteria go under Coverage Gaps, never silently dropped.
- An untestable criterion is a requirements defect: report it, do not rewrite
  it inside the test plan.

## Document shape — ISO/IEC/IEEE 29119-3

Clause numbers here are the 2013 edition (the current 2021 edition renumbers);
the document *names* carry across editions.

- **Test Plan** carries context, risk register, test strategy, activities and
  estimates, staffing, schedule. A missing section is a finding, not a style
  choice.
- **Test Case** = preconditions, inputs, expected results, unique ID (§4.12). A
  case with no expected result can neither pass nor fail.
- **Test traceability matrix** (§4.33, the `Verifies:` column): closes every AC
  in one direction and every TC in the other. An orphan in either direction is a
  defect — an AC with no case, a case with no criterion.
- Full conformance requires every information item; tailored conformance requires
  written justification for each item omitted. Produce only what this plan needs
  and say which items you left out.

## Minimal worked example

```gherkin
Feature: Create order

  Scenario: Valid payload
    Given a customer with a valid cart
    When they POST /orders
    Then the response is 201 with an order id
```

## Common failure modes

- One e2e case covering five criteria: nothing localises the failure.
- `Given/When/Then` written as prose inside a single line — unparseable.
- Test cases for behaviour no criterion states.
