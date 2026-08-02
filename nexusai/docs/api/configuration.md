# Configuration Reference

Nexus AI reads all configuration from the environment. This page describes the settings
groups and how to inspect them; the complete variable list is in the
[Environment reference](environment.md).

## Inspecting configuration

```bash
nexusai config        # print the effective, resolved configuration
```

## Settings groups

| Group | Key | Purpose |
|---|---|---|
| Environment | `NEXUSAI_ENVIRONMENT` | Profile: `local`, `ci`, `staging`, `production` |
| Logging | `NEXUSAI_LOGGING__*` | Level, console format, optional file logging |
| Paths | `NEXUSAI_PATHS__ROOT` | Root for data, artefacts, reports, logs and state |
| Plugins | `NEXUSAI_PLUGINS__*` | Load behaviour (e.g. fail on load error) |

Nested keys use a double underscore: `NEXUSAI_LOGGING__CONSOLE__FORMAT` maps to
`logging.console.format`.

## Application configuration

Each application adds its own environment-driven settings:

| Application | Prefix | Reference |
|---|---|---|
| REST API | `NEXUSAI_PRO_` | [Environment](environment.md#rest-api) |
| Enterprise | `NEXUSAI_ENT_` | [Environment](environment.md#enterprise) |
| Scheduler | `NEXUSAI_SCHED_` | [Environment](environment.md#scheduler) |
| Desktop | `NEXUSAI_` | [Environment](environment.md#desktop) |

## Precedence

1. Process environment variables
2. A local `.env` file (development convenience only; git-ignored)
3. Built-in defaults

!!! warning "Secrets"
    Secrets live in the environment only — never in a YAML file, a log, or a report.
