# Configuration

Nexus AI is configured entirely from the environment (12-factor). This page explains the
model; the [API → Configuration](../api/configuration.md) and
[API → Environment](../api/environment.md) references list every option.

## The model

- All variables use the `NEXUSAI_` prefix.
- Nested settings use a **double underscore** as the separator:
  `NEXUSAI_LOGGING__LEVEL` maps to `logging.level`.
- Real environment variables always win over an optional `.env` file, so `.env` can never
  override a deployment.

```bash
cp .env.example .env      # local convenience only; git-ignored
```

## Common settings

```bash
# Environment profile: local | ci | staging | production
export NEXUSAI_ENVIRONMENT=production

# Logging
export NEXUSAI_LOGGING__LEVEL=INFO           # TRACE..CRITICAL
export NEXUSAI_LOGGING__CONSOLE__FORMAT=json # console | json

# Where data, artefacts, reports, logs and state are written
export NEXUSAI_PATHS__ROOT=/var/lib/nexusai

# Fail fast if a plugin cannot load (recommended in production)
export NEXUSAI_PLUGINS__FAIL_ON_LOAD_ERROR=true
```

## Precedence

1. Explicit process environment variables
2. Values from a local `.env` file (development convenience)
3. Built-in defaults

!!! warning "Secrets"
    Secrets (for example the enterprise signing key) belong in the environment only. They
    are never written to a YAML file, logged, or included in a report.

See the complete list in the [Environment reference](../api/environment.md).
