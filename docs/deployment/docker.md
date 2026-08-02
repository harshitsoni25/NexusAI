# Docker

Nexus AI ships container assets for running the engine and services in Docker. The base
image is minimal by design.

## Image

The image builds the engine, sets a non-root user, and uses `nexusai` as its
entrypoint:

```bash
docker build -t nexusai .
docker run --rm nexusai doctor
docker run --rm nexusai version
```

## Running a scrape with persistence

Mount a volume at the data root so datasets, reports and state survive container restarts
and are visible to other containers:

```bash
docker run --rm \
  -e NEXUSAI_PATHS__ROOT=/data \
  -v nexusai-data:/data \
  nexusai scrape https://example.com --export csv --report html
```

A job persisted by one container can be inspected or resumed from another that mounts the
same volume.

## Compose

`docker-compose.yml` wires the service, its data volume and network. Validate and bring it
up with:

```bash
docker compose config       # validate
docker compose up           # run
```

## Services

To run the REST and enterprise APIs, build a Python image that installs the applications
and launch them with an ASGI server:

```bash
uvicorn nexusai_pro_api.main:app --host 0.0.0.0 --port 8000
uvicorn 'nexusai_pro_enterprise.app.api:create_enterprise_app' --factory \
        --host 0.0.0.0 --port 8080
```

Serve the built web and reporting UIs (`npm run build` → `dist/`) from a static host or
CDN.

!!! note "Minimal image"
    Optional export formats and browser binaries are not installed in the base image by
    design. Add the extras you need in a derived image.
