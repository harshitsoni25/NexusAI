# Plugin System

Plugins are Python distributions that implement one or more extension points and are
discovered from their `nexusai.plugins` entry points. The engine validates and loads
them; the plugin manager adds install/enable/disable/remove on top.

## Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Installed: pip install (distribution<br/>with entry point)
    Installed --> Discovered: engine scans<br/>nexusai.plugins
    Discovered --> Validated: check api_version<br/>+ extension point
    Validated --> Loaded: accepted
    Validated --> Rejected: reason recorded
    Loaded --> Enabled: default / admin enables
    Enabled --> Disabled: admin disables (reversible)
    Disabled --> Enabled: re-enabled
    Loaded --> Removed: uninstall
    Enabled --> Removed: uninstall
    Rejected --> Removed: uninstall
    Removed --> [*]

    note right of Rejected
        Surfaced as data with a reason —
        never raised as an error
    end note
```

## Discovery & correlation

```mermaid
flowchart TB
    PIP["Installed distributions"] --> EP["entry points<br/>group: nexusai.plugins"]
    EP --> DISC["PluginDiscovery"]
    DISC --> REP["LoadReport<br/>accepted[] · rejected[]"]
    REP --> REG["InMemoryPluginRegistry"]
    REG --> RESOLVE["resolution<br/>effective plugin set"]

    classDef frozen fill:#0f766e,stroke:#0c5c56,color:#fff;
    class DISC,REP,REG frozen;
```

## Compatibility

Each extension point carries its own **API version** (`major.minor`), independent of the
framework release. A plugin is compatible when it targets the same major version and a
minor version no greater than the framework's — additive changes never break existing
plugins.

For the contracts, see the [Plugin API](../plugins/plugin-api.md); to write one, see
[Plugin Development](../plugins/plugin-development.md).
