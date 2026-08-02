"""Bounded process resource sampling using only the standard library.

Resource sampling reads the operating system for CPU time and memory. To respect
dependency governance, it uses only the standard library and introduces no
third-party monitoring package.

The primitive it reads depends on the platform, because the stdlib exposes process
metrics differently on each. On POSIX (Linux, macOS) :mod:`resource` provides
cumulative CPU time and peak resident set size. On Windows :mod:`resource` does not
exist, so CPU comes from :func:`time.process_time` and resident set size from the
Win32 ``GetProcessMemoryInfo`` API through :mod:`ctypes`. Either way the values are
real -- nothing is fabricated -- and Python's own allocation is offered separately
through :mod:`tracemalloc`, never conflated with the OS figure.

The Unix-only :mod:`resource` import is guarded so that importing Nexus AI never
requires it: the sampler is only exercised by benchmarking, but the framework's
composition root imports this module eagerly, so the guard is what keeps the whole
framework importable on Windows.

CPU *utilisation* is not read directly; it is derived from the change in CPU time
over a wall-clock interval by the pure ``summarise`` helper.
"""

from __future__ import annotations

import os
import sys
import time
import tracemalloc
from types import ModuleType

from nexusai.domain.observability.resources import ResourceSample

resource: ModuleType | None
try:  # POSIX only; absent on Windows.
    import resource as _resource_module
except ModuleNotFoundError:  # pragma: no cover - platform-dependent
    resource = None
else:
    resource = _resource_module


class ResourceSampler:
    """Samples process CPU and memory using the standard library only."""

    def sample(self) -> ResourceSample:
        """Take a point-in-time resource sample.

        Reads CPU and resident set size from whichever standard-library primitive
        the platform exposes. Raises if a platform provides neither, rather than
        report a fabricated figure.
        """
        cpu_seconds, rss_bytes = _read_cpu_and_rss()
        python_allocated: int | None = None
        if tracemalloc.is_tracing():
            python_allocated = tracemalloc.get_traced_memory()[0]
        return ResourceSample(
            cpu_seconds=cpu_seconds,
            rss_bytes=rss_bytes,
            python_allocated_bytes=python_allocated,
            monotonic_seconds=time.monotonic(),
        )

    @property
    def cpu_count(self) -> int | None:
        """The number of CPUs available, for interpreting utilisation."""
        return os.cpu_count()


def _current_platform() -> str:
    """Return ``sys.platform`` as a plain string.

    The indirection keeps the platform value opaque to static narrowing, so the
    Windows branch below is type-checked rather than pruned as unreachable on a
    POSIX checker host.
    """
    return sys.platform


def _read_cpu_and_rss() -> tuple[float, int]:
    """Return ``(cpu_seconds, rss_bytes)`` from the platform's stdlib primitive."""
    if resource is not None:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        return usage.ru_utime + usage.ru_stime, _max_rss_bytes(usage.ru_maxrss)
    if _current_platform() == "win32":
        return time.process_time(), _windows_rss_bytes()
    raise RuntimeError("resource sampling is not supported on this platform")


def _max_rss_bytes(ru_maxrss: int) -> int:
    """Convert ``ru_maxrss`` to bytes, accounting for the platform's unit.

    On Linux ``ru_maxrss`` is in kilobytes; on macOS it is already in bytes.
    """
    if sys.platform == "darwin":
        return ru_maxrss
    return ru_maxrss * 1024


def _windows_rss_bytes() -> int:  # pragma: no cover - exercised only on Windows
    """Return the current working-set size in bytes via the Win32 API.

    Uses ``GetProcessMemoryInfo`` through :mod:`ctypes`; no third-party dependency.
    The function signatures are declared explicitly: ``GetCurrentProcess`` returns a
    pointer-sized ``HANDLE``, and without ``restype``/``argtypes`` ctypes would
    marshal it as a 32-bit ``c_int``, truncating the handle on 64-bit Windows and
    producing ``ERROR_INVALID_HANDLE`` (WinError 6).
    """
    import ctypes
    from ctypes import wintypes

    class _ProcessMemoryCounters(ctypes.Structure):
        _fields_ = (
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        )

    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    psapi = ctypes.windll.psapi  # type: ignore[attr-defined]

    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.GetCurrentProcess.argtypes = ()

    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    psapi.GetProcessMemoryInfo.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(_ProcessMemoryCounters),
        wintypes.DWORD,
    )

    counters = _ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(_ProcessMemoryCounters)
    handle = kernel32.GetCurrentProcess()
    if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
        raise ctypes.WinError()  # type: ignore[attr-defined]
    return int(counters.WorkingSetSize)
