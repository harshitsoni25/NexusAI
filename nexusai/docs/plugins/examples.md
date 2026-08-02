# Plugin Examples

A complete, minimal exporter plugin you can copy.

## Project layout

```text
acme-csv/
├── pyproject.toml
└── acme_csv/
    ├── __init__.py
    └── plugin.py
```

## `acme_csv/plugin.py`

```python
from nexusai.domain.model.plugin import (
    ApiVersion, ExtensionPoint, PluginMetadata,
)

class AcmeCsvExporter:
    """A minimal exporter plugin."""

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
        pass

    def dispose(self) -> None:
        pass

def build() -> AcmeCsvExporter:
    return AcmeCsvExporter()
```

## `pyproject.toml`

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "acme-csv"
version = "1.0.0"
requires-python = ">=3.12"

[project.entry-points."nexusai.plugins"]
acme-csv = "acme_csv.plugin:build"
```

## Install and confirm

```bash
pip install -e .
nexusai plugins
# exporter:acme-csv  1.0.0  (api 1.0)  loaded
```

## Managing it at runtime

Once installed, the plugin can be curated with the plugin manager:

```python
from nexusai_pro_plugins import build_manager

mgr = build_manager()
mgr.list_plugins()          # includes acme-csv with its load state
mgr.disable("acme-csv")     # reversible; stays installed
mgr.enable("acme-csv")
```

See [Administration → Scheduler](../administration/scheduler.md) for running plugins on a
schedule, and the [Plugin API](plugin-api.md) for the full contracts.
