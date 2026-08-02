# Diagram Reference

A single place for the platform's cross-cutting diagrams. Diagrams specific to a subsystem
live with their prose:

- [System architecture](overview.md#system-architecture)
- [Dependency injection](dependency-injection.md#engine-composition-root)
- [Request lifecycle (sequence)](request-lifecycle.md#submitting-a-scrape)
- [Scheduler pipeline & state machine](scheduler.md#pipeline)
- [Plugin lifecycle](plugin-system.md#lifecycle)
- [Reporting data flow](reporting.md#data-flow)

## Component & dependency map

```mermaid
flowchart LR
    subgraph UI["UI (TypeScript)"]
        WEB["pro/web"]
        REP["pro/reporting"]
        DESK["pro/desktop"]
    end
    subgraph PY["Services (Python)"]
        API["pro/api"]
        ENT["pro/enterprise"]
        SCHED["pro/scheduler"]
        PLUG["pro/plugins"]
    end
    subgraph ENGINE["Engine (frozen)"]
        GW{{"engine gateway"}}
        RUN{{"ScrapeRunner"}}
        CAT{{"plugin catalog"}}
        CORE["Scraping engine"]
    end

    DESK --> WEB
    WEB --> API
    REP --> API
    WEB --> ENT
    API --> GW
    SCHED --> RUN
    PLUG --> CAT
    GW --> CORE
    RUN --> CORE
    CAT --> CORE

    classDef frozen fill:#0f766e,stroke:#0c5c56,color:#fff;
    class CORE frozen;
    classDef seam fill:#e0f2f1,stroke:#0d9488,color:#0f766e;
    class GW,RUN,CAT seam;
```

The teal nodes are the only seams that touch the engine.

## CLI execution flow

```mermaid
flowchart TB
    CMD["nexusai scrape &lt;target&gt;"] --> PARSE["parse args + options"]
    PARSE --> BOOT["bootstrap(config_file)"]
    BOOT --> CONT["Container"]
    CONT --> RT["build_scrape_runtime()"]
    CONT --> COLLAB["build_scrape_collaborators(...)"]
    RT --> UC["StartScrapeUseCase"]
    COLLAB --> UC
    UC --> WF

    subgraph WF["Workflow stages"]
        direction LR
        R["retrieve"] --> X["extract"] --> P["process"] --> V["validate"] --> PE["persist"] --> E["export"] --> RP["report"]
    end

    WF --> OUT["ScrapeOutcome"]
    OUT --> RENDER["render to stdout"]
    OUT --> FILES["export + report files"]

    classDef frozen fill:#0f766e,stroke:#0c5c56,color:#fff;
    class BOOT,CONT,RT,COLLAB,UC,WF,R,X,P,V,PE,E,RP,OUT frozen;
```

The API's gateway and the scheduler's runner invoke the **same** use-cases the CLI uses;
only the front-end differs.
