# Changelog

All notable changes to Nexus AI are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0]

The first public release of Nexus AI.

### Engine

- Certified, plugin-driven scraping engine with a clean layered architecture and a
  composition root.
- Ten published extension points discovered from installed Python distributions.
- Synchronous domain with an async-capable I/O edge; job state machine with checkpointing
  and resume.
- Structured logging with correlation IDs, a doctor/health command, and separate
  operational and dataset stores.
- CLI: `scrape`, `resume`, `jobs`, `stats`, `doctor`, `export`, `report`, `plugins`,
  `schedule`, `config`, `datasets`, `diagnose`, `benchmark`, `analyze`, `version`.
- Exporters for CSV, JSON and NDJSON; HTML and JSON reports.

### Applications

- **REST API** — FastAPI service exposing the engine with structured logging and a typed
  error envelope.
- **Web app** — React + TypeScript operator UI.
- **Desktop app** — hardened Electron shell with native integration, splash, About dialog,
  crash reporting and auto-update.
- **Scheduler** — cron/daily/weekly/monthly scheduling with a worker pool, retry/backoff
  and notifications.
- **Plugin manager** — install, update, enable/disable and remove plugins.
- **Reporting** — analytics UI: KPIs, success rate, trends, execution time, storage usage,
  a sandboxed report viewer and export preview.
- **Enterprise** — multi-tenant authentication, RBAC, projects, teams, API keys, audit
  logs and workspace management; cloud-ready.

### Certification

- **C1** real-browser, **C2** Docker environment, **C3** hosted CI, and **C4**
  vulnerability scan — all passed. Production-ready.

[0.1.0]: https://github.com/nexusai/nexusai/releases/tag/v0.1.0
