# Project Structure

The repository is a monorepo: a certified engine plus applications that build on it.

```text
nexusai/
├── src/nexusai/            # Certified scraping engine (frozen)
│   ├── domain/                #   entities, value objects, policies, ports
│   ├── application/           #   use-cases (scrape, resume, queries, doctor)
│   ├── infrastructure/        #   adapters: storage, exporters, plugins, browser
│   └── presentation/cli/      #   the nexusai command-line interface
├── pro/                       # Applications built on the engine
│   ├── api/                   #   FastAPI REST service
│   ├── web/                   #   React operator UI
│   ├── desktop/               #   Electron shell
│   ├── scheduler/             #   scheduling service
│   ├── plugins/               #   plugin manager
│   ├── reporting/             #   analytics UI
│   ├── enterprise/            #   tenancy / RBAC layer
│   └── release/ci/            #   release automation
├── docs/                      # This documentation site (MkDocs Material)
├── config/                    # Configuration profiles
├── docker/                    # Container assets
├── tests/                     # Engine test suite
└── pyproject.toml             # Engine packaging
```

## Engine layering

Dependencies point inward: `presentation` → `application` → `domain`, with
`infrastructure` implementing the domain's ports. The **composition root**
(`src/nexusai/composition/`) is the only place that wires concrete adapters to ports.

## Applications

Each directory under `pro/` is an independently installable component with its own tests
and packaging. They depend on the engine as a library and never modify it.
