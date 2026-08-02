"""Application factory for the Nexus AI Pro API.

Builds the FastAPI app: a lifespan that constructs the engine gateway and the
background job runner once and stores them on ``app.state``; a request-id
middleware for log correlation; CORS; the engine/API exception handlers; and the
seven resource routers mounted under the configured API prefix. FastAPI generates
the OpenAPI schema and serves Swagger UI and ReDoc automatically.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from nexusai_pro_api.config import ApiSettings, get_settings
from nexusai_pro_api.errors import register_exception_handlers
from nexusai_pro_api.logging_config import (
    configure_logging,
    get_logger,
    new_request_id,
    request_id_var,
)
from nexusai_pro_api.routers import (
    exports,
    health,
    jobs,
    plugins,
    reports,
    scraping,
    statistics,
)
from nexusai_pro_api.services.engine_gateway import EngineGateway
from nexusai_pro_api.services.job_runner import JobRunner

logger = get_logger("main")

OPENAPI_TAGS = [
    {"name": "Health", "description": "Liveness and engine readiness (doctor) checks."},
    {"name": "Scraping", "description": "Submit and resume scrapes; runs off the event loop."},
    {"name": "Jobs", "description": "List and inspect engine jobs and their state."},
    {"name": "Statistics", "description": "Aggregate job/throughput statistics from durable data."},
    {"name": "Plugins", "description": "Plugins discovered by the engine and any load failures."},
    {"name": "Exports", "description": "Dataset exports (produced during scraping)."},
    {"name": "Reports", "description": "Dataset reports (produced during scraping)."},
]


class _RequestIdMiddleware(BaseHTTPMiddleware):
    """Assign a request id for the duration of each request and echo it in a header."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        token = request_id_var.set(new_request_id())
        try:
            response = await call_next(request)
        finally:
            rid = request_id_var.get()
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = rid
        return response


def create_app(settings: ApiSettings | None = None) -> FastAPI:
    """Construct and return a configured FastAPI application."""
    settings = settings or get_settings()
    configure_logging(level=settings.log_level, as_json=settings.log_json)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logger.info("building engine gateway")
        gateway = EngineGateway.create(config_file=settings.engine_config_file)
        runner = JobRunner(gateway, max_workers=settings.max_concurrent_scrapes)
        app.state.gateway = gateway
        app.state.job_runner = runner
        logger.info("startup complete")
        try:
            yield
        finally:
            runner.shutdown()
            logger.info("shutdown complete")

    app = FastAPI(
        title=settings.title,
        version=settings.version,
        description=settings.description,
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        openapi_url=settings.openapi_url,
        openapi_tags=OPENAPI_TAGS,
        root_path=settings.root_path,
        lifespan=lifespan,
    )

    app.add_middleware(_RequestIdMiddleware)
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    register_exception_handlers(app)

    prefix = settings.api_prefix
    for module in (health, scraping, jobs, statistics, plugins, exports, reports):
        app.include_router(module.router, prefix=prefix)

    return app


app = create_app()
