# Core Concepts

A short glossary of the ideas you'll meet throughout Nexus AI.

Engine
:   The certified scraping core — a synchronous, plugin-aware library and CLI with clean
    domain/application/infrastructure layers. It is reused unchanged by every application.

Job
:   A single scrape execution. It moves through the workflow stages (retrieve → extract →
    process → validate → persist → export → report) and ends in a terminal state. Jobs are
    checkpointed and can be resumed.

Dataset
:   The persisted output of a scrape, identified by a dataset id and version, stored with
    metadata and provenance.

Extension point
:   One of ten published contracts the engine exposes (site adapter, scraping strategy,
    extractor, validator, DQA rule, exporter, storage provider, report generator,
    middleware, notification).

Plugin
:   A Python distribution that implements one or more extension points and is discovered
    from its `nexusai.plugins` entry points.

Schedule
:   A recurring trigger (cron/daily/weekly/monthly) that enqueues scrapes for the
    scheduler's worker pool.

Workspace
:   The enterprise tenant boundary. Users, teams, projects, API keys and audit entries all
    belong to exactly one workspace.

Principal
:   The authenticated subject of a request — a user (via token) or a machine (via API key)
    — carrying its workspace and roles for authorization.

!!! abstract "One core, many front-ends"
    The CLI, REST API and scheduler all compose the same engine use-cases. See the
    [Architecture overview](../architecture/overview.md).
