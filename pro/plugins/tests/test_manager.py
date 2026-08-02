"""PluginManager behaviour with a fake catalog and a fake pip runner."""

from __future__ import annotations

from nexusai_pro_plugins import (
    CatalogEntry,
    EnablementStore,
    PluginInstaller,
    PluginManager,
    PluginSource,
    RuntimePlugin,
    RuntimeState,
)


class FakeCatalog:
    def __init__(self, entries):
        self._entries = entries

    def entries(self):
        return list(self._entries)


class FakeRunner:
    def __init__(self):
        self.calls = []
        self.returncode = 0

    def run(self, args):
        self.calls.append(args)
        return self.returncode, f"ran pip {' '.join(args)}", ""


def _entry(pid, dist="dist-" + "x", version="1.0.0", state=RuntimeState.LOADED):
    return CatalogEntry(
        id=pid,
        source=PluginSource.ENTRY_POINT,
        distribution=dist,
        distribution_version=version,
        state=state,
        runtime=RuntimePlugin(name=pid, version=version, api_version="1.0", extension_point="exporter", description="d"),
    )


def _manager(tmp_path, entries, runner=None):
    catalog = FakeCatalog(entries)
    installer = PluginInstaller(runner or FakeRunner())
    enablement = EnablementStore(tmp_path / "en.json")
    return PluginManager(catalog, installer, enablement)


def test_list_and_details(tmp_path):
    mgr = _manager(tmp_path, [_entry("csv-plus"), _entry("sitemap")])
    views = mgr.list_plugins()
    assert [v.id for v in views] == ["csv-plus", "sitemap"]  # sorted
    assert all(v.enabled for v in views)
    detail = mgr.details("csv-plus")
    assert detail and detail.runtime.version == "1.0.0" and detail.runtime.extension_point == "exporter"
    assert mgr.details("nope") is None


def test_enable_disable_affects_effective_set(tmp_path):
    mgr = _manager(tmp_path, [_entry("csv-plus"), _entry("sitemap")])
    assert set(mgr.effective_plugin_names()) == {"csv-plus", "sitemap"}
    mgr.disable("sitemap")
    assert mgr.details("sitemap").enabled is False
    assert mgr.details("sitemap").active is False
    assert set(mgr.effective_plugin_names()) == {"csv-plus"}
    mgr.enable("sitemap")
    assert set(mgr.effective_plugin_names()) == {"csv-plus", "sitemap"}


def test_rejected_plugin_never_effective(tmp_path):
    rejected = _entry("broken", state=RuntimeState.REJECTED)
    rejected.runtime = None
    rejected.reason = "does not satisfy the plugin contract"
    mgr = _manager(tmp_path, [rejected])
    view = mgr.details("broken")
    assert view.state is RuntimeState.REJECTED and view.reason
    assert mgr.effective_plugin_names() == []  # rejected excluded even though enabled


def test_install_update_remove_invoke_pip(tmp_path):
    runner = FakeRunner()
    mgr = _manager(tmp_path, [_entry("csv-plus", dist="nexusai-csv-plus")], runner)

    r = mgr.install("nexusai-csv-plus", version="2.1.0")
    assert r.ok and ["install", "nexusai-csv-plus==2.1.0"] in runner.calls

    r = mgr.update("nexusai-csv-plus")
    assert r.ok and ["install", "--upgrade", "nexusai-csv-plus"] in runner.calls

    r = mgr.remove("csv-plus")  # resolves to its distribution
    assert r.ok and ["uninstall", "-y", "nexusai-csv-plus"] in runner.calls


def test_remove_forgets_enablement(tmp_path):
    runner = FakeRunner()
    mgr = _manager(tmp_path, [_entry("csv-plus", dist="nexusai-csv-plus")], runner)
    mgr.disable("csv-plus")
    assert mgr.details("csv-plus").enabled is False
    mgr.remove("csv-plus")
    # after removal its enablement state is forgotten (would default enabled if reinstalled)
    assert EnablementStore(tmp_path / "en.json").is_enabled("csv-plus") is True


def test_install_failure_surfaces(tmp_path):
    runner = FakeRunner()
    runner.returncode = 1
    mgr = _manager(tmp_path, [], runner)
    r = mgr.install("does-not-exist")
    assert r.ok is False and r.action == "install"
