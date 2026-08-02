# Development

How to set up a working environment and make changes.

## Setup

```bash
git clone https://github.com/nexusai/nexusai
cd nexusai
pip install -e ".[dev]"
pip install -e pro/api -e pro/scheduler -e pro/plugins -e "pro/enterprise[dev]"
(cd pro/web && npm ci); (cd pro/reporting && npm ci); (cd pro/desktop && npm ci)
```

## Make targets (engine)

| Target | Action |
|---|---|
| `make install` | install the engine with dev extras |
| `make format` | format the codebase |
| `make lint` | run ruff |
| `make typecheck` | run mypy |
| `make test` | run the test suite |
| `make check` | format check + lint + typecheck + tests |
| `make build` | build the distribution |
| `make clean` | remove build artefacts |

## Component workflows

=== "Python (api · scheduler · plugins · enterprise)"

    ```bash
    cd pro/<component>
    ruff check .
    mypy <package> --ignore-missing-imports
    pytest
    ```

=== "TypeScript (web · reporting)"

    ```bash
    cd pro/<component>
    npm run typecheck
    npm run build
    npm run dev
    ```

=== "Desktop (electron)"

    ```bash
    cd pro/desktop
    npm run build          # tsc
    npm run dist:linux     # or dist:win / dist:mac
    ```

## Conventions

- Reuse the engine only through its composition root; keep the seam small.
- Depend on **ports/protocols**, not concrete adapters.
- Every component owns its tests and must stay green.
- Use [Conventional Commits](https://www.conventionalcommits.org/).

See [Testing](testing.md) and [Debugging](debugging.md) next.
