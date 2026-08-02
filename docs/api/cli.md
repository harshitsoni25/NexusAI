# CLI Reference

The `nexusai` command is the primary interface to the engine. Run `nexusai --help`
or `nexusai <command> --help` for full option listings.

## Commands

| Command | Purpose |
|---|---|
| `scrape` | Run a scrape against a target |
| `resume` | Continue a checkpointed job |
| `jobs` | List jobs and their state |
| `stats` | Show aggregate statistics |
| `datasets` | Inspect stored datasets |
| `export` | Produce an export in a chosen format |
| `report` | Produce a report |
| `plugins` | List discovered plugins and their status |
| `schedule` | Manage schedules |
| `config` | Show effective configuration |
| `doctor` | Run environment and readiness checks |
| `diagnose` | Deeper diagnostics for troubleshooting |
| `benchmark` | Run performance benchmarks |
| `analyze` | Analyse a target or dataset |
| `version` | Print the version |

## Common usage

=== "Scrape"

    ```bash
    nexusai scrape https://example.com --export csv --report html
    ```

=== "Resume"

    ```bash
    nexusai resume <job-id>
    ```

=== "Inspect"

    ```bash
    nexusai jobs
    nexusai stats
    nexusai datasets
    ```

=== "Plugins"

    ```bash
    nexusai plugins
    ```

=== "Health"

    ```bash
    nexusai doctor
    nexusai version
    ```

## Exit codes

Commands return conventional exit codes: `0` on success and non-zero on failure, so they
compose in scripts and CI. Use `nexusai diagnose` when a command fails and the cause is
not obvious.

## Scheduling from the CLI

```bash
nexusai schedule        # manage recurring scrapes
```

For running the scheduler as a service, see
[Administration → Scheduler](../administration/scheduler.md).
