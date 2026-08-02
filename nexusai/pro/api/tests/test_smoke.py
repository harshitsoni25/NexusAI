"""Smoke tests for the Nexus AI Pro API.

These verify the app wires up: the engine gateway builds from the real engine, all
routers are mounted, health responds, and the OpenAPI schema is generated. They use
FastAPI's TestClient, which drives the app through its lifespan (so the engine is
actually bootstrapped).
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from nexusai_pro_api.main import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_health_liveness() -> None:
    with _client() as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_openapi_served() -> None:
    with _client() as client:
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "Nexus AI Pro API"


def test_expected_routes_registered() -> None:
    app = create_app()
    paths = set(app.openapi()["paths"].keys())
    for expected in (
        "/api/v1/health",
        "/api/v1/health/ready",
        "/api/v1/scrape",
        "/api/v1/scrape/{submission_id}",
        "/api/v1/scrape/{job_id}/resume",
        "/api/v1/jobs",
        "/api/v1/jobs/{job_id}",
        "/api/v1/statistics",
        "/api/v1/plugins",
        "/api/v1/exports",
        "/api/v1/reports",
    ):
        assert expected in paths, f"missing route: {expected}"


def test_readiness_runs_engine_doctor() -> None:
    with _client() as client:
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200
        assert response.json()["ready"] is True


def test_request_id_header_present() -> None:
    with _client() as client:
        response = client.get("/api/v1/health")
        assert "X-Request-ID" in response.headers


def test_jobs_list_ok() -> None:
    with _client() as client:
        response = client.get("/api/v1/jobs")
        assert response.status_code == 200
        body = response.json()
        assert "jobs" in body and "count" in body
