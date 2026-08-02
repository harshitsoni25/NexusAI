# Contributing to Nexus AI

Thank you for helping improve Nexus AI! This guide covers setup, the change workflow,
and the quality bar every contribution must meet.

## The golden rule

The certified engine under `src/nexusai/` is **frozen**. Its content is verified
byte-for-byte in CI. New capabilities are added through **plugins** or the applications
under `pro/`, never by editing the engine. A change to the engine requires a separate,
re-certified engine revision.

## Development setup

Prerequisites: Python 3.12+, Node 22+, npm 10+.

```bash
git clone https://nexusai.github.io/nexusai-repo
cd nexusai
pip install -e ".[dev]"                       # engine + tooling
pip install -e pro/api -e pro/scheduler -e pro/plugins -e "pro/enterprise[dev]"
(cd pro/web && npm ci)
(cd pro/reporting && npm ci)
(cd pro/desktop && npm ci)
```

## Change workflow

1. Create a branch: `git checkout -b feat/short-description`.
2. Keep changes scoped to one component under `pro/` or to a plugin.
3. Add or update tests for any behaviour you change.
4. Run the quality gates for the components you touched.
5. Update the docs under `docs/` if behaviour or interfaces change.

## Quality gates

```bash
# Python components
make check                 # format check + lint + typecheck + tests (engine)
cd pro/<component> && ruff check . && mypy <package> && pytest

# TypeScript components
cd pro/<web|reporting|desktop> && npm run typecheck && npm run build
```

## Coding standards

- **Python** — ruff (`E,F,I,UP,B,SIM`) and mypy clean; small, typed, testable units;
  depend on protocols/ports, not concrete adapters.
- **TypeScript** — strict `tsc`; keep the API behind an interface with a mock
  implementation.
- **Commits** — [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).

## Pull requests

- Describe the change and link any related issue.
- Confirm the quality gates pass.
- Keep PRs focused; split large changes.
- By contributing you agree your work is licensed under the [MIT License](LICENSE).

## Code of Conduct

Participation is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). Report security
issues via the [Security Policy](SECURITY.md), not public issues.
