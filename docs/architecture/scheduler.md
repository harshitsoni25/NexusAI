# Scheduler Architecture

The scheduler turns schedules into background scrapes: it computes due times, enqueues
jobs, runs them through a worker pool, and retries with backoff — notifying at each
transition.

## Pipeline

```mermaid
flowchart TB
    CRON["cron / daily / weekly / monthly<br/>schedules"] --> LOOP["SchedulerLoop<br/>tick()"]
    LOOP --> DUE{"due now?"}
    DUE -->|yes| ENQ["enqueue QueuedJob"]
    DUE -->|no| WAIT["wait for next tick"]
    ENQ --> Q[("JobQueue<br/>heap · delayed visibility")]
    Q --> POOL["worker pool"]
    POOL --> RUN["EngineScrapeRunner"]
    RUN --> ENG["engine workflow"]
    RUN --> RES{"result"}
    RES -->|success| DONE["completed"]
    RES -->|failure| RETRY{"retries left?"}
    RETRY -->|yes| BACK["backoff → requeue"]
    RETRY -->|no| DLQ["dead-letter"]
    BACK --> Q
    DONE --> NOTIFY["notify"]
    DLQ --> NOTIFY
    NOTIFY --> SINKS["Logging · Console · Webhook"]

    classDef frozen fill:#0f766e,stroke:#0c5c56,color:#fff;
    class ENG frozen;
```

## Run state machine

```mermaid
stateDiagram-v2
    [*] --> Queued
    Queued --> Running: worker picks up
    Running --> Completed: success
    Running --> Failed: error
    Failed --> Retrying: attempts remain
    Retrying --> Queued: after exponential backoff
    Failed --> DeadLetter: attempts exhausted
    Completed --> [*]
    DeadLetter --> [*]
```

!!! info "Backoff never busy-loops"
    Retries use the queue's **delayed visibility**: a retried job is invisible to workers
    until its backoff elapses, so waiting costs nothing.

Operating the scheduler is covered in [Administration → Scheduler](../administration/scheduler.md).
