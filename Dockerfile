# Nexus AI runtime image.
#
# A slim, non-root image that installs the built wheel and exposes the CLI as the
# entrypoint. The framework is synchronous and pure-Python at its core; no browser
# binary is installed here because browser retrieval is an optional capability
# (see the deployment guide). Data, artifacts, reports, logs and state live under
# a single writable root the container owns.
FROM python:3.12-slim AS build
WORKDIR /build
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip install --no-cache-dir --upgrade pip build \
    && python -m build --wheel

FROM python:3.12-slim AS runtime
# Create an unprivileged user; the framework never needs root.
RUN useradd --create-home --uid 10001 harvest
WORKDIR /home/harvest
COPY --from=build /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm -f /tmp/*.whl
# The writable root for all outputs, owned by the unprivileged user.
ENV NEXUSAI_PATHS__ROOT=/data
RUN mkdir -p /data && chown -R harvest:harvest /data
USER harvest
ENTRYPOINT ["nexusai"]
CMD ["--help"]
