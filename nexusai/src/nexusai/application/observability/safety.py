"""Failure isolation for observability.

Observability must not break the thing it observes. A metrics sink that raises, a
resource sampler that fails, a log sink that is momentarily unavailable -- none of
these should terminate a running job. This module provides the boundary that
enforces that policy: work inside :func:`safely` that raises is caught, optionally
logged as a warning, and swallowed, so the core operation continues.

Fatal isolation is deliberately not the default. Only an explicit audit or
compliance requirement would justify letting an observability failure stop a job,
and that would be a conscious configuration, not an accident.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from nexusai.domain.ports.observability import Logger


@contextmanager
def safely(operation: str, *, logger: Logger | None = None) -> Iterator[None]:
    """Run an observability operation, swallowing any error as non-critical.

    Args:
        operation: A short label naming what was attempted, for the warning.
        logger: When given, a warning is logged; otherwise the error is silent.
    """
    try:
        yield
    except Exception as error:  # noqa: BLE001 - observability must never propagate
        if logger is not None:
            logger.warning("observability.suppressed", operation=operation, error=str(error))
