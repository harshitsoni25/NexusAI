# Nexus AI

**Nexus AI** is a production-grade web-scraping platform: a certified, plugin-driven
scraping engine and a suite of applications built around it — a REST API, web and desktop
clients, a scheduler, plugin management, analytics and multi-tenant enterprise features.

[![Docs](https://img.shields.io/badge/docs-mkdocs--material-0f766e)](https://nexusai.github.io/nexusai/)
[![License: MIT](https://img.shields.io/badge/license-MIT-informational)](LICENSE)
[![Certified](https://img.shields.io/badge/certification-C1--C4%20passed-15803d)](https://nexusai.github.io/nexusai/quality/certification/)

## Highlights

- **Clean, layered engine** — a synchronous, plugin-aware scraping core with clear
  domain/application/infrastructure boundaries and a composition root.
- **Extensible** — ten published extension points discovered from installed Python
  distributions; add capabilities without touching the core.
- **Complete surface** — CLI, REST API, React web app, Electron desktop app, a scheduler,
  a reporting/analytics UI, and an enterprise tenancy layer.
- **Operable** — structured logging with correlation, health/doctor checks, an audit
  trail, and native crash reporting.
- **Certified & frozen** — the engine passes C1–C4 certification and is reused unchanged
  across every component.

## Quick start

```bash
pip install -e ".[dev]"
nexusai doctor
nexusai scrape https://example.com --export csv --report html
```

Prefer a UI? Start the API and web app:

```bash
uvicorn nexusai_pro_api.main:app --port 8000     # REST API
cd pro/web && npm ci && npm run dev                 # web UI at http://localhost:5173
```

See the [Installation guide](https://nexusai.github.io/nexusai/getting-started/installation/)
and [Quickstart](https://nexusai.github.io/nexusai/getting-started/quickstart/).

## Documentation

Full documentation is published at **https://nexusai.github.io/nexusai/** and lives
in [`docs/`](docs/). Build it locally with:

```bash
pip install mkdocs-material
mkdocs serve
```

## Project layout

```text
src/nexusai/   Certified scraping engine (CLI + library)
pro/              Applications built on the engine (api, web, desktop, scheduler,
                  plugins, reporting, enterprise)
docs/             This documentation site (MkDocs Material)
```

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) and our
[Code of Conduct](CODE_OF_CONDUCT.md). For security reports, follow the
[Security Policy](SECURITY.md).

## License

Released under the [MIT License](LICENSE).
