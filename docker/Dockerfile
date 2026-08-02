# ---------------------------------------------------------------------------
# Nexus AI development and test image.
#
# Multi-stage so that the runtime image contains the installed package and its
# dependencies but none of the build toolchain. Deployment concerns -- registries,
# orchestration, secrets management -- are deliberately out of scope here.
# ---------------------------------------------------------------------------

ARG PYTHON_VERSION=3.12

# --------------------------------------------------------------------------- #
# Builder
# --------------------------------------------------------------------------- #
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# Copy only what the build needs, so that a source change does not invalidate
# the dependency layer.
COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN python -m pip install --upgrade pip build \
 && python -m build --wheel --outdir /dist

# --------------------------------------------------------------------------- #
# Runtime
# --------------------------------------------------------------------------- #
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    NEXUSAI_ENVIRONMENT=production \
    NEXUSAI_PATHS__ROOT=/var/lib/nexusai

# Running as root inside a container that fetches untrusted remote content is an
# unnecessary risk, so the framework runs as an unprivileged user.
RUN groupadd --system nexusai \
 && useradd --system --gid nexusai --create-home --home-dir /home/nexusai nexusai

WORKDIR /app

COPY --from=builder /dist/*.whl /tmp/
RUN python -m pip install /tmp/*.whl && rm -rf /tmp/*.whl

COPY config ./config

RUN mkdir -p /var/lib/nexusai && chown -R nexusai:nexusai /var/lib/nexusai /app

USER nexusai

# Fails the container if the framework cannot start, load configuration and
# discover plugins -- which is precisely what `diagnose` verifies.
HEALTHCHECK --interval=60s --timeout=15s --start-period=10s --retries=3 \
  CMD ["nexusai", "diagnose"]

ENTRYPOINT ["nexusai"]
CMD ["--help"]

# --------------------------------------------------------------------------- #
# Development: editable install plus the full toolchain, for running the checks
# inside a container identical to CI.
# --------------------------------------------------------------------------- #
FROM python:${PYTHON_VERSION}-slim AS development

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    NEXUSAI_ENVIRONMENT=local

RUN apt-get update \
 && apt-get install -y --no-install-recommends make git \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip install --upgrade pip && python -m pip install -e ".[dev,test]"

COPY . .
CMD ["make", "check"]
