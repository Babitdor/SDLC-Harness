---
name: api-design
description: Design a REST endpoint contract and its OpenAPI 3.0 document from user stories and the data model, then validate it to zero errors with openapi_validator_tool. Use whenever design/API_SPEC.md or design/openapi.yaml is being written or repaired.
license: proprietary
---

## When to use

You are @API, or repairing an existing `design/openapi.yaml`. Read
`requirements/USER_STORIES.md` (what the endpoint must serve) and
`design/DATA_MODEL.md` (which fields the payloads may contain).

## Rules

- Target OpenAPI 3.0.3. `openapi: 3.0.3` is the first key.
- Every path starts with `/`; every operation has `operationId` and `responses`.
- Every response declares a schema or a `$ref`; a `$ref` must resolve inside
  `components/schemas`.
- Field names match DATA_MODEL.md exactly — no renaming in transit.
- One error response minimum per operation, with a real condition, not "error".
- No invented auth schemes, rate limits or pagination that no story asks for.

## Minimal worked example

```yaml
openapi: 3.0.3
info: {title: Orders, version: 0.1.0}
paths:
  /orders:
    post:
      operationId: createOrder
      responses:
        '201':
          description: created
          content:
            application/json:
              schema: {$ref: '#/components/schemas/Order'}
        '400':
          description: invalid payload
components:
  schemas:
    Order:
      type: object
      required: [id]
      properties:
        id: {type: string}
```

## Common failure modes

- YAML that parses but is rejected by the spec schema: missing `responses`,
  a path not starting with `/`, an unquoted `200` key (becomes an integer).
- A `$ref` to a schema that was never defined.
- API_SPEC.md and openapi.yaml drifting apart — fix the side that is wrong,
  then re-check both against each other.
