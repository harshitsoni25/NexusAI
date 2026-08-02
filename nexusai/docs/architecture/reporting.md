# Reporting Architecture

The reporting app is a read-only analytics surface. It derives what it can from the
existing API and fills the rest from a mock provider — no new backend endpoints are added.

## Data flow

```mermaid
flowchart TB
    subgraph Backend["REST API (unchanged)"]
        STATS["/statistics"]
        JOBS["/jobs"]
    end

    API["ReportingApi (interface)"]
    HTTP["HttpReportingApi"]
    MOCK["mockApi"]

    STATS --> HTTP
    JOBS --> HTTP
    HTTP -->|derive| DERIVED["KPIs · success rate · statistics"]
    HTTP -->|reuse for series| SERIES["trends · execution time · storage"]
    MOCK --> SERIES
    API --> HTTP
    API --> MOCK

    DERIVED --> SECTIONS
    SERIES --> SECTIONS

    subgraph SECTIONS["Reporting sections"]
        OV["Overview<br/>KPIs · success donut · trends"]
        PERF["Performance<br/>exec-time histogram · storage"]
        ST["Statistics table"]
        RV["Report viewer<br/>(sandboxed iframe)"]
        EP["Export preview<br/>csv · json · ndjson"]
    end
```

!!! note "Live vs illustrative"
    KPIs, success rate and the statistics table are **live** against a connected backend.
    Trends, execution time and storage series are **illustrative** unless a metrics source
    is wired — adding one would change the backend, which reporting deliberately avoids.

## Safe report rendering

```mermaid
sequenceDiagram
    autonumber
    participant UI as Report viewer
    participant API as ReportingApi
    participant IFRAME as Sandboxed iframe

    UI->>API: reportDocument(id)
    API-->>UI: { html }
    UI->>IFRAME: srcDoc = html, sandbox=""
    Note over IFRAME: empty sandbox — no scripts, no same-origin
```

The report viewer renders report HTML inside an iframe with an **empty sandbox**, so
engine-produced artefacts display without running code or reaching the parent page.
