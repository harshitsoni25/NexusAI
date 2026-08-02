# Certification

Nexus AI's engine is certified against four gates. A gate is **PASS** only when real
execution evidence exists. All four pass; the platform is production-ready.

!!! success "Production readiness: READY"
    C1, C2, C3 and C4 all pass. The engine is reused unchanged across the platform.

## Gate summary

| Gate | Status | Evidence |
|---|---|---|
| **C1 — Real browser** | :material-check-circle:{ .pass } PASS | 12 of 12 browser tests passed on Windows with real Chromium |
| **C2 — Docker environment** | :material-check-circle:{ .pass } PASS | Real-container build, runtime/doctor, cross-container persistence, and exports |
| **C3 — Hosted CI** | :material-check-circle:{ .pass } PASS | GitHub Actions green: quality (Python 3.12 + 3.13), portability (Windows + macOS), build |
| **C4 — Vulnerability scan** | :material-check-circle:{ .pass } PASS | Dependency audit over the deployable set; the sole finding is non-applicable |

## C1 — Real browser

Real Chromium on Windows: **12 selected, 12 passed, 0 failed**. This exercises the actual
browser-automation path.

## C2 — Docker environment

Verified against real containers:

- **Build / image** — all build steps succeed; a non-root user; entrypoint `nexusai`.
- **Runtime / doctor** — version reports `0.1.0`; the doctor's required checks pass.
- **Workflow + persistence** — a scrape completes and a job is recovered from a *separate*
  container (stats: total = 1, completed = 1, health = pass).
- **Exports** — CSV, JSON, HTML report and NDJSON generated and content-verified; NDJSON
  confirmed readable from a fresh container.
- **Compose** — configuration valid, image built, doctor passes, cleanup passes.

!!! note "Documented N/A items"
    Optional Excel/Parquet/PDF exporters and an in-image browser binary are **not
    applicable** by the minimal-image deployment contract.

## C3 — Hosted CI

The hosted pipeline is green across quality (Python 3.12 and 3.13), portability (Windows
and macOS) and build. See [CI/CD](ci-cd.md).

## C4 — Vulnerability scan

A dependency audit over the deployable set reported a single advisory, assessed as **not
applicable**:

- **CVE-2026-41066** — an `lxml` XXE local-file-read via entity resolution.
- **Assessment: not applicable.** The XML parser is hardened (`resolve_entities=False`,
  `no_network=True`), HTML parsing uses a safe default, and no unsafe-by-default parsers
  are used.
- **Decision: non-blocking**, documented. No other advisories were found.

## Provenance

The certification applies to the frozen engine (digest `c28c2a74…`) that every application
reuses. Any change to the engine would require a new, separately certified revision — see
the [Roadmap](../about/roadmap.md).
