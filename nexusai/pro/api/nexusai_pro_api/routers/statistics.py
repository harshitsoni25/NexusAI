"""Statistics endpoint: aggregate engine metrics."""

from __future__ import annotations

from fastapi import APIRouter

from nexusai_pro_api.dependencies import GatewayDep
from nexusai_pro_api.schemas.statistics import StatisticsModel

router = APIRouter(prefix="/statistics", tags=["Statistics"])


@router.get("", response_model=StatisticsModel, summary="Aggregate statistics")
def statistics(gateway: GatewayDep) -> StatisticsModel:
    """Return job/throughput statistics computed by the engine from durable data."""
    return StatisticsModel.from_engine(gateway.statistics())
