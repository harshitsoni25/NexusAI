"""Export and report operations over datasets.

The engine produces exports and reports as *stages of a scrape*, operating on the
in-memory ``ProcessedDataset`` while it is being built. Its persisted form
(``StoredDataset``) keeps only version metadata and provenance — not the processed
records — so the frozen engine offers no way to rehydrate a dataset and re-export it
after the fact. Rather than reconstruct engine internals (which would mean modifying
the certified engine), these operations reflect that boundary: exports and reports
are requested at scrape time via ``export_formats`` / ``report_formats`` on
``POST /scrape``.

If a future engine capability adds dataset rehydration, only this module changes; the
routers and schemas already model the resource.
"""

from __future__ import annotations

from typing import Any

from fastapi import status

from nexusai_pro_api.errors import ApiError
from nexusai_pro_api.services.engine_gateway import EngineGateway

_GUIDANCE = (
    "Exports and reports are produced during a scrape. Submit POST /api/v1/scrape "
    "with the desired export_formats/report_formats; the engine writes the artifacts "
    "as part of the workflow. Re-exporting a previously stored dataset is not supported "
    "by the engine, whose persisted form retains version metadata and provenance only."
)


def export_dataset(gateway: EngineGateway, *, dataset_id: str, fmt: str) -> Any:
    """Export a stored dataset — unsupported by the frozen engine (see module docstring)."""
    raise ApiError(
        status.HTTP_501_NOT_IMPLEMENTED,
        "not_supported",
        f"Standalone export of stored dataset '{dataset_id}' as '{fmt}' is not available. {_GUIDANCE}",
    )


def report_dataset(gateway: EngineGateway, *, dataset_id: str, fmt: str) -> Any:
    """Report on a stored dataset — unsupported by the frozen engine (see module docstring)."""
    raise ApiError(
        status.HTTP_501_NOT_IMPLEMENTED,
        "not_supported",
        f"Standalone report of stored dataset '{dataset_id}' as '{fmt}' is not available. {_GUIDANCE}",
    )
