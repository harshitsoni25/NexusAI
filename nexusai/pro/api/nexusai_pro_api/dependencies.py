"""Dependency injection for the API.

The engine gateway and the job runner are process-wide singletons created during
application startup (see ``main.lifespan``) and stored on ``app.state``. The provider
functions below expose them to routers through FastAPI's ``Depends`` so handlers
never import the engine or construct collaborators themselves.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from nexusai_pro_api.services.engine_gateway import EngineGateway
from nexusai_pro_api.services.job_runner import JobRunner


def get_gateway(request: Request) -> EngineGateway:
    """Return the shared engine gateway built at startup."""
    gateway: EngineGateway | None = getattr(request.app.state, "gateway", None)
    if gateway is None:  # pragma: no cover - startup guarantees this
        raise RuntimeError("Engine gateway is not initialised")
    return gateway


def get_job_runner(request: Request) -> JobRunner:
    """Return the shared background job runner built at startup."""
    runner: JobRunner | None = getattr(request.app.state, "job_runner", None)
    if runner is None:  # pragma: no cover - startup guarantees this
        raise RuntimeError("Job runner is not initialised")
    return runner


GatewayDep = Annotated[EngineGateway, Depends(get_gateway)]
JobRunnerDep = Annotated[JobRunner, Depends(get_job_runner)]
