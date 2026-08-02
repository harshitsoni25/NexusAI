# Debugging

Techniques for diagnosing issues during development and in the field.

## Health and doctor

```bash
nexusai doctor        # required checks; run this first
```

The doctor reports environment prerequisites and plugin load status. A failing check names
the problem and the remedy.

## Logging

Raise the log level to see the framework's decisions:

```bash
export NEXUSAI_LOGGING__LEVEL=DEBUG      # TRACE for maximum detail
nexusai scrape https://example.com
```

Enable durable JSON logs on disk for later inspection:

```bash
export NEXUSAI_LOGGING__FILE__ENABLED=true
```

Every log line carries a **correlation id**; the REST API additionally returns a
`request_id` (also the `X-Request-ID` header) so a client action can be traced to its
server logs.

## Inspecting jobs

```bash
nexusai jobs          # list jobs and their state
nexusai stats         # aggregate statistics
nexusai resume <id>   # continue a checkpointed job
```

## Plugins

```bash
nexusai plugins       # loaded and rejected plugins, with reasons
```

A rejected plugin is reported as data with a reason (incompatible API version, failed
load) rather than raising.

## Desktop crashes

Native crash dumps and a JSON error log are written under `…/Nexus AI/crashes/`. Set
`NEXUSAI_CRASH_URL` to forward crashes to a collector. Include these plus the About
details when filing an issue.
