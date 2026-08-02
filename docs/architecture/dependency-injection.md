# Dependency Injection

Nexus AI wires collaborators through composition roots rather than global state. This
makes every component testable with fakes and makes persistence swappable.

## Engine composition root

`bootstrap()` returns a fully wired container; applications build their collaborators from
it.

```mermaid
flowchart TB
    BOOT["bootstrap(config_file)"] --> CONT["Container<br/>plugins · id_generator · logger · correlation_id"]
    CONT --> RT["build_scrape_runtime(container)"]
    RT --> JM["JobManager"]
    RT --> CM["CheckpointManager"]
    CONT --> COLLAB["build_scrape_collaborators(...)"]
    COLLAB --> UC["Scrape use-cases<br/>StartScrapeUseCase · ResumeJobUseCase"]
    JM --> UC
    CM --> UC

    classDef frozen fill:#0f766e,stroke:#0c5c56,color:#fff;
    class BOOT,CONT,RT,COLLAB,JM,CM,UC frozen;
```

`bootstrap` lives in `nexusai.composition.container`; `build_scrape_runtime` and
`build_scrape_collaborators` live in `nexusai.composition.application`. Use-cases take
keyword-only collaborators and expose an `execute(...)` method.

## Enterprise container

The enterprise layer selects repository adapters from configuration and injects them into
services.

```mermaid
flowchart LR
    CFG["EnterpriseConfig<br/>(env / 12-factor)"] --> CONT["EnterpriseContainer"]
    CONT --> REPOS{"backend?"}
    REPOS -->|memory| MEM["in-memory repositories"]
    REPOS -->|sql / cloud| SQL["durable repositories"]
    CONT --> TOK["TokenService (HMAC)"]
    MEM --> SVC["services"]
    SQL --> SVC
    TOK --> SVC
    SVC --> AUTH["AuthService"]
    SVC --> RBAC["Authorizer"]
    SVC --> REST["user · workspace · project · team · apikey · audit"]

    classDef swap stroke-dasharray:5 5,fill:#f0fdfa,stroke:#0d9488,color:#0f766e;
    class SQL swap;
```

The dashed adapter is the cloud swap-in point — services depend on repository **ports**,
so switching persistence is a wiring change, not a code change.

## Why it matters

<div class="grid cards" markdown>

-   :material-test-tube:{ .lg .middle } **Testability**

    ---

    Services accept protocol-typed collaborators, so tests inject fakes — no network, no
    database.

-   :material-swap-horizontal:{ .lg .middle } **Swappable persistence**

    ---

    Repositories are ports; the in-memory adapters ship by default and a durable adapter is
    a one-line wiring change.

-   :material-lock:{ .lg .middle } **One place for secrets**

    ---

    The signing secret and backend selection live in the container, never scattered through
    the code.

</div>
