# Plugin Development

Extend Nexus AI by packaging a Python distribution that implements one or more
[extension points](plugin-api.md#extension-points). The engine discovers it from its
entry points — no core changes required.

## Anatomy of a plugin

A plugin is:

1. an object satisfying the [`Plugin` protocol](plugin-api.md#the-plugin-protocol)
   (a `metadata` property plus `initialize()` and `dispose()`),
2. a **builder** callable that returns that object, and
3. an entry point in the `nexusai.plugins` group pointing at the builder.

## Step 1 — implement the plugin

```python
# acme_csv/plugin.py
from nexusai.domain.model.plugin import (
    ApiVersion, ExtensionPoint, PluginMetadata,
)

class AcmeCsvExporter:
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="acme-csv",
            version="1.0.0",
            extension_point=ExtensionPoint.EXPORTER,
            api_version=ApiVersion(1, 0),
            description="Acme CSV exporter",
            author="Acme, Inc.",
        )

    def initialize(self) -> None:
        ...   # acquire resources if needed

    def dispose(self) -> None:
        ...   # release resources

def build() -> AcmeCsvExporter:
    return AcmeCsvExporter()
```

## Step 2 — declare the entry point

=== "pyproject.toml"

    ```toml
    [project]
    name = "acme-csv"
    version = "1.0.0"

    [project.entry-points."nexusai.plugins"]
    acme-csv = "acme_csv.plugin:build"
    ```

## Step 3 — install and verify

```bash
pip install -e .
nexusai plugins        # acme-csv should appear as loaded
```

If it appears under rejected, the reason is shown — usually an incompatible
[API version](plugin-api.md#api-versions) or a load error.

## Guidelines

- Keep `metadata` a **property**; return a fully-populated `PluginMetadata`.
- Target the lowest `api_version` you need; you stay compatible with later framework
  minors automatically.
- Do heavy work in `initialize()`, release it in `dispose()`.
- Name plugins uniquely within their extension point.

A complete, runnable example is in [Examples](examples.md).
