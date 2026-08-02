"""Plugin discovery."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest

from nexusai.domain.errors import PluginError
from nexusai.domain.model.plugin import ApiVersion, ExtensionPoint, PluginMetadata
from nexusai.infrastructure.config.settings import PluginSettings
from nexusai.infrastructure.plugins import discovery as discovery_module
from nexusai.infrastructure.plugins.discovery import PluginDiscovery
from nexusai.infrastructure.plugins.registry import InMemoryPluginRegistry
from nexusai.testing import RecordingLogger, StubPlugin

# Referenced by allow-list specifications below. The test module is already
# imported, so it resolves without a separate fixture file on disk.
MODULE = __name__


def GoodPlugin() -> StubPlugin:  # noqa: N802 - referenced as a factory by name
    """Factory for a well-formed plugin."""
    return StubPlugin(name="good")


def FuturePlugin() -> StubPlugin:  # noqa: N802
    """A plugin targeting a contract version this framework does not provide."""
    return StubPlugin(name="future", api_version=ApiVersion(9, 0))


def ExplodingPlugin() -> StubPlugin:  # noqa: N802
    """A factory that fails."""
    raise RuntimeError("cannot construct")


class NotAPlugin:
    """Satisfies nothing."""


@dataclass
class RaisingMetadataPlugin:
    """A plugin whose metadata property fails."""

    @property
    def metadata(self) -> Any:
        raise RuntimeError("metadata unavailable")

    def initialize(self) -> None:
        return None

    def dispose(self) -> None:
        return None


@dataclass
class BadMetadataPlugin:
    """Declares metadata of the wrong type."""

    @property
    def metadata(self) -> Any:
        return "not metadata"

    def initialize(self) -> None:
        return None

    def dispose(self) -> None:
        return None


@pytest.fixture
def no_entry_points(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate discovery from whatever happens to be installed."""
    monkeypatch.setattr(
        discovery_module, "importlib_metadata", SimpleNamespace(entry_points=lambda **_: ())
    )


def discover(
    settings: PluginSettings, logger: RecordingLogger
) -> tuple[Any, InMemoryPluginRegistry]:
    registry = InMemoryPluginRegistry()
    report = PluginDiscovery(settings=settings, logger=logger).discover(registry)
    return report, registry


def test_discovery_can_be_switched_off(logger: RecordingLogger) -> None:
    report, registry = discover(PluginSettings(discovery_enabled=False), logger)
    assert report.accepted == () and len(registry) == 0


def test_an_allowlisted_plugin_is_registered(
    logger: RecordingLogger, no_entry_points: None
) -> None:
    report, registry = discover(PluginSettings(allowlist=(f"{MODULE}:GoodPlugin",)), logger)
    assert [item.name for item in report.accepted] == ["good"]
    assert registry.has(ExtensionPoint.EXPORTER, "good")


def test_an_unimportable_module_is_rejected_not_fatal(
    logger: RecordingLogger, no_entry_points: None
) -> None:
    # One broken third-party plugin must never prevent the framework from running.
    report, _ = discover(PluginSettings(allowlist=("nonexistent.module:Thing",)), logger)
    assert report.has_failures
    assert "could not be imported" in report.rejected[0].reason


def test_a_missing_attribute_is_rejected(logger: RecordingLogger, no_entry_points: None) -> None:
    report, _ = discover(PluginSettings(allowlist=(f"{MODULE}:Absent",)), logger)
    assert "does not define this attribute" in report.rejected[0].reason


@pytest.mark.parametrize("spec", ["no_colon", ":Attribute", "module:"])
def test_a_malformed_specification_is_rejected(
    spec: str, logger: RecordingLogger, no_entry_points: None
) -> None:
    report, _ = discover(PluginSettings(allowlist=(spec,)), logger)
    assert "module:attribute" in report.rejected[0].reason


def test_a_failing_constructor_is_rejected(logger: RecordingLogger, no_entry_points: None) -> None:
    report, _ = discover(PluginSettings(allowlist=(f"{MODULE}:ExplodingPlugin",)), logger)
    assert "constructor raised RuntimeError" in report.rejected[0].reason


def test_an_object_that_is_not_a_plugin_is_rejected(
    logger: RecordingLogger, no_entry_points: None
) -> None:
    report, _ = discover(PluginSettings(allowlist=(f"{MODULE}:NotAPlugin",)), logger)
    assert "does not satisfy the plugin contract" in report.rejected[0].reason


def test_metadata_of_the_wrong_type_is_rejected(
    logger: RecordingLogger, no_entry_points: None
) -> None:
    report, _ = discover(PluginSettings(allowlist=(f"{MODULE}:BadMetadataPlugin",)), logger)
    assert "not a PluginMetadata" in report.rejected[0].reason


def test_a_plugin_whose_metadata_raises_is_rejected(
    logger: RecordingLogger, no_entry_points: None
) -> None:
    report, _ = discover(PluginSettings(allowlist=(f"{MODULE}:RaisingMetadataPlugin",)), logger)
    assert "metadata raised RuntimeError" in report.rejected[0].reason


def test_an_incompatible_contract_version_is_rejected(
    logger: RecordingLogger, no_entry_points: None
) -> None:
    report, registry = discover(PluginSettings(allowlist=(f"{MODULE}:FuturePlugin",)), logger)
    assert report.has_failures
    assert len(registry) == 0


def test_a_disabled_plugin_is_skipped_without_being_called_a_failure(
    logger: RecordingLogger, no_entry_points: None
) -> None:
    report, registry = discover(
        PluginSettings(allowlist=(f"{MODULE}:GoodPlugin",), disabled=("good",)), logger
    )
    assert report.accepted == () and report.rejected == ()
    assert len(registry) == 0


def test_a_plugin_can_be_disabled_by_qualified_name(
    logger: RecordingLogger, no_entry_points: None
) -> None:
    report, _ = discover(
        PluginSettings(allowlist=(f"{MODULE}:GoodPlugin",), disabled=("exporter:good",)), logger
    )
    assert report.accepted == ()


def test_strict_deployments_can_make_a_rejection_fatal(
    logger: RecordingLogger, no_entry_points: None
) -> None:
    settings = PluginSettings(allowlist=("nonexistent.module:Thing",), fail_on_load_error=True)
    with pytest.raises(PluginError, match="fail_on_load_error"):
        discover(settings, logger)


def test_every_rejection_is_logged(logger: RecordingLogger, no_entry_points: None) -> None:
    # A plugin that silently failed to load looks identical to one never installed.
    discover(PluginSettings(allowlist=("nonexistent.module:Thing",)), logger)
    assert logger.has_message("Plugin rejected", level="WARNING")


def test_entry_points_are_consulted(
    logger: RecordingLogger, monkeypatch: pytest.MonkeyPatch
) -> None:
    @dataclass
    class FakeEntryPoint:
        name: str

        def load(self) -> object:
            return GoodPlugin

    monkeypatch.setattr(
        discovery_module,
        "importlib_metadata",
        SimpleNamespace(entry_points=lambda **_: (FakeEntryPoint("good"),)),
    )
    report, registry = discover(PluginSettings(), logger)
    assert len(registry) == 1
    assert report.accepted[0].name == "good"


def test_an_entry_point_that_fails_to_load_is_rejected(
    logger: RecordingLogger, monkeypatch: pytest.MonkeyPatch
) -> None:
    @dataclass
    class BrokenEntryPoint:
        name: str

        def load(self) -> object:
            raise ImportError("missing dependency")

    monkeypatch.setattr(
        discovery_module,
        "importlib_metadata",
        SimpleNamespace(entry_points=lambda **_: (BrokenEntryPoint("broken"),)),
    )
    report, _ = discover(PluginSettings(), logger)
    assert "missing dependency" in report.rejected[0].reason


def test_the_report_summarises_both_outcomes(
    logger: RecordingLogger, no_entry_points: None
) -> None:
    report, _ = discover(
        PluginSettings(allowlist=(f"{MODULE}:GoodPlugin", "nonexistent.module:Thing")), logger
    )
    assert report.summary() == "1 plugin(s) loaded, 1 rejected"


def test_a_rejection_renders_readably() -> None:
    rejected = discovery_module.RejectedPlugin("pkg:thing", "because")
    assert str(rejected) == "pkg:thing: because"


def test_rejected_references_are_extractable(
    logger: RecordingLogger, no_entry_points: None
) -> None:
    report, _ = discover(PluginSettings(allowlist=("nonexistent.module:Thing",)), logger)
    assert discovery_module.rejected_references(report) == ["nonexistent.module:Thing"]


def test_the_entry_point_group_is_configurable() -> None:
    settings = PluginSettings(entry_point_group="custom.group")
    assert discovery_module.entry_point_group_of(settings) == "custom.group"


def test_metadata_is_well_formed_for_the_stub() -> None:
    assert isinstance(GoodPlugin().metadata, PluginMetadata)


def _unused() -> Iterator[None]:  # pragma: no cover - keeps the import list honest
    yield None
