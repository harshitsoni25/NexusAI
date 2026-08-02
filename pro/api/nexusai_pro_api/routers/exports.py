"""Exports endpoint: export a stored dataset via the engine's export stage."""

from __future__ import annotations

from fastapi import APIRouter, status

from nexusai_pro_api.dependencies import GatewayDep
from nexusai_pro_api.schemas.exports import ExportManifestModel, ExportRequest

router = APIRouter(prefix="/exports", tags=["Exports"])


@router.post(
    "",
    response_model=ExportManifestModel,
    status_code=status.HTTP_201_CREATED,
    summary="Export a stored dataset",
)
def create_export(body: ExportRequest, gateway: GatewayDep) -> ExportManifestModel:
    """Export the latest stored version of a dataset in the requested format.

    Reuses the engine's export stage; supported core formats are csv, json and
    ndjson (others require the corresponding optional engine extra).
    """
    from nexusai_pro_api.services.export_ops import export_dataset

    manifest = export_dataset(gateway, dataset_id=body.dataset_id, fmt=body.format)
    return ExportManifestModel(
        dataset_id=body.dataset_id,
        format=body.format,
        location=getattr(manifest, "location", None) or getattr(manifest, "destination", None),
        record_count=getattr(manifest, "record_count", None),
    )
