"""Portability regression tests for resource sampling (Windows defect 10R-CV-R1).

A real Windows run failed at import because ``resources.py`` imported the Unix-only
``resource`` module unconditionally, and the composition root imports that module
eagerly. These tests protect the actual failure path -- the import chain -- with
``resource`` forced unavailable, and verify the sampler dispatches to the Windows
primitive and degrades nothing to a fabricated figure. They run on any platform.
"""

from __future__ import annotations

import builtins
import importlib
import sys
from collections.abc import Iterator

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def without_resource() -> Iterator[None]:
    """Make ``import resource`` fail and purge nexusai modules, then restore."""
    real_import = builtins.__import__

    def blocked(name: str, *args: object, **kwargs: object) -> object:
        if name == "resource":
            raise ModuleNotFoundError("No module named 'resource'")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    saved = {k: v for k, v in sys.modules.items() if k.startswith("nexusai") or k == "resource"}
    for key in saved:
        sys.modules.pop(key, None)
    builtins.__import__ = blocked  # type: ignore[assignment]
    try:
        yield
    finally:
        builtins.__import__ = real_import
        for key in list(sys.modules):
            if key.startswith("nexusai") or key == "resource":
                sys.modules.pop(key, None)
        sys.modules.update(saved)


class TestImportChainWithoutResource:
    def test_observability_package_imports(self, without_resource: None) -> None:
        module = importlib.import_module("nexusai.infrastructure.observability")
        assert hasattr(module, "ResourceSampler")

    def test_resources_module_imports(self, without_resource: None) -> None:
        module = importlib.import_module("nexusai.infrastructure.observability.resources")
        assert module.resource is None  # guarded import fell back to None

    def test_composition_container_imports(self, without_resource: None) -> None:
        module = importlib.import_module("nexusai.composition.container")
        assert hasattr(module, "build_container")

    def test_cli_app_imports(self, without_resource: None) -> None:
        module = importlib.import_module("nexusai.presentation.cli.app")
        assert hasattr(module, "app")


class TestWindowsDispatch:
    def test_sample_uses_windows_rss_when_resource_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from nexusai.infrastructure.observability import resources

        monkeypatch.setattr(resources, "resource", None)
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setattr(resources, "_windows_rss_bytes", lambda: 4096)

        sample = resources.ResourceSampler().sample()
        assert sample.rss_bytes == 4096  # real platform figure, not fabricated 0
        assert sample.cpu_seconds >= 0.0  # from time.process_time()
        assert sample.monotonic_seconds > 0.0

    def test_unsupported_platform_raises_rather_than_fabricating(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from nexusai.infrastructure.observability import resources

        monkeypatch.setattr(resources, "resource", None)
        monkeypatch.setattr(sys, "platform", "sunos5")
        with pytest.raises(RuntimeError):
            resources.ResourceSampler().sample()


class TestPosixBehaviourPreserved:
    def test_linux_rss_is_kilobytes_scaled_to_bytes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from nexusai.infrastructure.observability import resources

        monkeypatch.setattr(sys, "platform", "linux")
        assert resources._max_rss_bytes(1000) == 1000 * 1024

    def test_macos_rss_is_already_bytes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from nexusai.infrastructure.observability import resources

        monkeypatch.setattr(sys, "platform", "darwin")
        assert resources._max_rss_bytes(2048) == 2048

    def test_real_posix_sample_reports_positive_rss(self) -> None:
        from nexusai.infrastructure.observability.resources import ResourceSampler

        if sys.platform == "win32":  # this assertion is for the POSIX primitive
            pytest.skip("POSIX-specific assertion")
        sample = ResourceSampler().sample()
        assert sample.rss_bytes > 0
        assert isinstance(sample.rss_bytes, int)


class TestWindowsCtypesSignatures:
    """Regression for the WinError 6 defect: Win32 signatures must be declared.

    Without ``restype``/``argtypes`` ctypes marshals the 64-bit process HANDLE as a
    32-bit int, truncating it and yielding ERROR_INVALID_HANDLE on 64-bit Windows.
    These tests inject a fake ``ctypes.windll`` so the declaration and control flow
    are verified deterministically on any OS; the real memory read is confirmed by
    the operator's Windows run.
    """

    def _fake_windll(self, *, success: int, working_set: int) -> object:

        class _Func:
            restype = None
            argtypes: object = None

            def __init__(self, side_effect: object) -> None:
                self._side_effect = side_effect

            def __call__(self, *args: object) -> object:
                return self._side_effect(*args)  # type: ignore[operator]

        class _Kernel32:
            GetCurrentProcess = _Func(lambda: 0xFFFFFFFFFFFFFFFF)

        def _get_process_memory_info(handle: object, ref: object, cb: object) -> int:
            if success:
                ref._obj.WorkingSetSize = working_set  # type: ignore[attr-defined]
            return success

        class _Psapi:
            GetProcessMemoryInfo = _Func(_get_process_memory_info)

        class _WinDLL:
            kernel32 = _Kernel32()
            psapi = _Psapi()

        return _WinDLL()

    def test_declares_signatures_and_reads_working_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import ctypes
        from ctypes import wintypes

        from nexusai.infrastructure.observability import resources

        fake = self._fake_windll(success=1, working_set=1_234_567)
        monkeypatch.setattr(ctypes, "windll", fake, raising=False)

        result = resources._windows_rss_bytes()

        assert result == 1_234_567  # WorkingSetSize read through the populated struct
        # The exact declarations that were missing and caused WinError 6:
        assert fake.kernel32.GetCurrentProcess.restype is wintypes.HANDLE  # type: ignore[attr-defined]
        gpmi = fake.psapi.GetProcessMemoryInfo  # type: ignore[attr-defined]
        assert gpmi.restype is wintypes.BOOL
        assert gpmi.argtypes[0] is wintypes.HANDLE
        assert gpmi.argtypes[2] is wintypes.DWORD
        assert len(gpmi.argtypes) == 3

    def test_api_failure_raises_rather_than_returning_bad_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import ctypes

        from nexusai.infrastructure.observability import resources

        fake = self._fake_windll(success=0, working_set=0)
        monkeypatch.setattr(ctypes, "windll", fake, raising=False)
        # ctypes.WinError exists only on Windows; provide it so the failure path
        # (which production reaches via ``raise ctypes.WinError()``) is testable here.
        monkeypatch.setattr(
            ctypes, "WinError", lambda *a, **k: OSError("simulated WinError"), raising=False
        )
        with pytest.raises(OSError):
            resources._windows_rss_bytes()
