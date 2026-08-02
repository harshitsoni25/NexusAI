# Testing Strategy

Quality is enforced by automated tests and static analysis at every layer, run locally and
in CI.

## Layered testing

| Layer | Approach |
|---|---|
| **Domain** | Fast unit tests over pure logic — versions, policies, state transitions. |
| **Application** | Use-case tests with fake collaborators injected through ports. |
| **Infrastructure** | Integration tests against real adapters (temporary stores, built fixture plugins). |
| **APIs** | Endpoint tests via the framework test client, asserting status codes and the error envelope. |
| **UI** | Type-checking and production builds; API access is behind a mockable interface. |

## Static analysis

- **Python** — `ruff` (lint + import order) and `mypy` (types) run clean.
- **TypeScript** — strict `tsc` type-checking and a successful production build.

## Determinism

Recorded fixtures make scraping tests deterministic, and injected fakes remove network and
database dependencies from unit and use-case tests. This keeps the suite fast and stable.

## Gates

A change is ready when, for the components it touches, lint/type checks pass, the tests
pass, and the build succeeds. These same gates run automatically in [CI/CD](ci-cd.md).
