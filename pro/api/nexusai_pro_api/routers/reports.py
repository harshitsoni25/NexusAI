"""Reports endpoint: generate a report for a stored dataset."""

from __future__ import annotations

from fastapi import APIRouter, status

from nexusai_pro_api.dependencies import GatewayDep
from nexusai_pro_api.schemas.reports import ReportManifestModel, ReportRequest

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post(
    "",
    response_model=ReportManifestModel,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a report for a stored dataset",
)
def create_report(body: ReportRequest, gateway: GatewayDep) -> ReportManifestModel:
    """Generate a report over the latest stored version of a dataset.

    Reuses the engine's report stage; html and json are always available.
    """
    from nexusai_pro_api.services.export_ops import report_dataset

    manifest = report_dataset(gateway, dataset_id=body.dataset_id, fmt=body.format)
    return ReportManifestModel(
        dataset_id=body.dataset_id,
        format=body.format,
        location=getattr(manifest, "location", None) or getattr(manifest, "destination", None),
    )
