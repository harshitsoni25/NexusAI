# Plugin API

The contracts a plugin implements. All types live in the engine's domain model and are
stable within a major API version.

## Extension points

A plugin implements one of ten published extension points:

| Extension point | Value | Extends |
|---|---|---|
| `SITE_ADAPTER` | `site_adapter` | Site-specific retrieval behaviour |
| `SCRAPING_STRATEGY` | `scraping_strategy` | How a page is scraped |
| `EXTRACTOR` | `extractor` | Turning content into records |
| `VALIDATOR` | `validator` | Validating records |
| `DQA_RULE` | `dqa_rule` | Data-quality assurance rules |
| `EXPORTER` | `exporter` | Writing datasets to a format |
| `STORAGE_PROVIDER` | `storage_provider` | Where datasets are stored |
| `REPORT_GENERATOR` | `report_generator` | Producing reports |
| `MIDDLEWARE` | `middleware` | Cross-cutting request/response behaviour |
| `NOTIFICATION` | `notification` | Delivering notifications |

```python
from nexusai.domain.model.plugin import ExtensionPoint
ExtensionPoint.EXPORTER          # ExtensionPoint
ExtensionPoint.EXPORTER.value    # "exporter"
```

## API versions

Each extension point carries its own two-part version, `major.minor`:

```python
from nexusai.domain.model.plugin import ApiVersion

v = ApiVersion(1, 0)             # or ApiVersion.parse("1.0")
str(v)                           # "1.0"
v.is_compatible_with(ApiVersion(1, 3))   # True  (same major, minor <=)
v.is_compatible_with(ApiVersion(2, 0))   # False (major differs)
```

Within a major version, changes are additive only — a plugin written against an earlier
minor still satisfies a later framework. A plugin written against a *later* minor may rely
on members the running framework does not yet provide, and is rejected.

## Plugin metadata

Every plugin describes itself with immutable metadata:

```python
from nexusai.domain.model.plugin import PluginMetadata, ExtensionPoint, ApiVersion

PluginMetadata(
    name="acme-csv",                       # unique within its extension point
    version="1.2.0",                        # the plugin's own version, opaque to the framework
    extension_point=ExtensionPoint.EXPORTER,
    api_version=ApiVersion(1, 0),           # the contract version implemented
    description="Acme CSV exporter",        # shown by `nexusai plugins`
    author="Acme, Inc.",
)
# .qualified_name -> "exporter:acme-csv"  (unique across the registry)
```

`name` and `version` must be non-empty.

## The Plugin protocol

A plugin is any object satisfying this protocol:

```python
from typing import Protocol
from nexusai.domain.model.plugin import PluginMetadata

class Plugin(Protocol):
    @property
    def metadata(self) -> PluginMetadata: ...   # a PROPERTY, not a method

    def initialize(self) -> None: ...           # called once on load
    def dispose(self) -> None: ...              # called on shutdown
```

!!! warning "`metadata` is a property"
    Expose `metadata` as a `@property`. The registry reads it as an attribute, not by
    calling a method.

## Discovery

Plugins are discovered from the `nexusai.plugins` entry-point group. Discovery produces
a `LoadReport` listing accepted plugins and rejected ones (each with a reason), and loaded
plugins are placed in an in-memory registry keyed by extension point and name.

See [Plugin Development](plugin-development.md) to package one and [Examples](examples.md)
for a complete plugin.
