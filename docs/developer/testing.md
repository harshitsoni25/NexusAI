# Testing

How to run and write tests across the platform.

## Running tests

=== "Engine"

    ```bash
    make test            # full engine suite
    pytest -k plugins    # a subset
    ```

=== "Application component"

    ```bash
    cd pro/<component>
    pytest               # component suite
    ```

## What to test

- **Domain** — pure logic (versions, policies, state transitions) with fast unit tests.
- **Application** — use-cases with fake collaborators injected through the ports.
- **Adapters** — integration tests against real implementations (a temporary store, a
  built fixture plugin).
- **APIs** — endpoint tests using the framework test client, asserting status codes and
  the error envelope.

## Fakes and fixtures

Because collaborators are injected through protocols, tests use in-memory fakes rather
than network or database access. The engine provides reusable test doubles for plugins;
the enterprise layer ships in-memory repositories used directly in tests.

## Quality gates

A change is ready when, for the components it touches:

- `ruff` and `mypy` are clean (Python) or `tsc` passes (TypeScript),
- the test suite passes,
- the build succeeds.

The [testing strategy](../quality/testing-strategy.md) describes coverage across the
platform, and [CI/CD](../quality/ci-cd.md) shows how these gates run automatically.
