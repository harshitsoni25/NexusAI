# Request Lifecycle

How a scrape flows through the REST API — from submission to a background run to progress
polling.

## Submitting a scrape

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as Web UI
    participant API as FastAPI router
    participant RUN as JobRunner<br/>(thread pool)
    participant GW as engine gateway
    participant ENG as Engine use-case
    participant DB as Dataset store

    User->>UI: Enter target + formats
    UI->>API: POST /api/v1/scrapes
    API->>API: attach request_id (contextvar)
    API->>RUN: submit(target, formats)
    API-->>UI: 202 Accepted { job_id }
    Note over API,UI: returns immediately — the event loop never blocks

    RUN->>GW: run scrape (off the event loop)
    GW->>ENG: StartScrapeUseCase.execute(...)
    ENG->>DB: persist dataset + provenance
    ENG-->>GW: ScrapeOutcome (job, result)
    GW-->>RUN: outcome
    RUN->>RUN: mark job completed
```

!!! tip "Non-blocking by construction"
    The synchronous engine runs inside a **bounded** thread pool
    (`NEXUSAI_PRO_MAX_CONCURRENT_SCRAPES`, 1–64). The HTTP response returns as soon as
    the job is accepted, so throughput is bounded by the pool, not by request handlers.

## Polling progress

```mermaid
sequenceDiagram
    autonumber
    participant UI as Web UI
    participant API as FastAPI router
    participant JM as JobManager

    loop until terminal state
        UI->>API: GET /api/v1/jobs/{id}
        API->>JM: get(job_id)
        JM-->>API: state + result
        API-->>UI: { state, stage, result }
    end
    Note over UI: stepper advances through the workflow stages
```

## Error handling

```mermaid
sequenceDiagram
    autonumber
    participant API as Router
    participant ENG as Engine
    participant ERR as error mapper

    API->>ENG: use-case call
    ENG--xAPI: raises NexusAIError(category=…)
    API->>ERR: map exception
    ERR-->>API: HTTP status + envelope
    API-->>API: { error: { code, message, request_id } }
```

Every failure becomes a stable, correlated envelope — no tracebacks leak, and the
`request_id` ties the response to the structured logs.
