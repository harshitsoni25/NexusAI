"""Health endpoints: liveness and engine readiness."""

from __future__ import annotations

from fastapi import APIRouter

from nexusai_pro_api.dependencies import GatewayDep
from nexusai_pro_api.schemas.health import Liveness, Readiness

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=Liveness, summary="Liveness probe")
def liveness() -> Liveness:
    """Return ok as long as the API process is serving requests."""
    return Liveness()


@router.get("/ready", response_model=Readiness, summary="Readiness / engine doctor")
def readiness(gateway: GatewayDep) -> Readiness:
    """Run the engine's doctor checks and report readiness."""
    report = gateway.doctor()
    to_dict = getattr(report, "to_dict", None)
    checks = to_dict() if callable(to_dict) else {}
    return Readiness(ready=True, checks=checks)
