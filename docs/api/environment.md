# Environment Reference

Every supported environment variable. All use the `NEXUSAI_` prefix; engine settings
use a double underscore for nesting (`NEXUSAI_LOGGING__LEVEL` → `logging.level`).

## Engine

| Variable | Default | Purpose |
|---|---|---|
| `NEXUSAI_ENVIRONMENT` | `local` | Profile: `local`, `ci`, `staging`, `production` |
| `NEXUSAI_LOGGING__LEVEL` | `INFO` | `TRACE`, `DEBUG`, `INFO`, `SUCCESS`, `WARNING`, `ERROR`, `CRITICAL` |
| `NEXUSAI_LOGGING__CONSOLE__FORMAT` | `console` | `console` or `json` |
| `NEXUSAI_LOGGING__FILE__ENABLED` | `false` | Enable durable JSON logs on disk |
| `NEXUSAI_PATHS__ROOT` | `./.nexusai` | Root for data, artefacts, reports, logs, state |
| `NEXUSAI_PLUGINS__FAIL_ON_LOAD_ERROR` | `false` | Abort startup if a plugin fails to load (recommended in production) |

## REST API

`NEXUSAI_PRO_` prefix.

| Variable | Default | Purpose |
|---|---|---|
| `NEXUSAI_PRO_MAX_CONCURRENT_SCRAPES` | `4` | Worker-pool size (1–64) |
| `NEXUSAI_PRO_CORS_ORIGINS` | *(empty)* | Allowed CORS origins |

## Enterprise

`NEXUSAI_ENT_` prefix.

| Variable | Default | Purpose |
|---|---|---|
| `NEXUSAI_ENT_SECRET` | `dev-insecure-change-me` | Token signing secret (**must** be set in production) |
| `NEXUSAI_ENT_TOKEN_TTL` | `3600` | Token lifetime (seconds) |
| `NEXUSAI_ENT_ISSUER` | `nexusai-pro` | Token issuer claim |
| `NEXUSAI_ENT_MIN_PW` | `10` | Minimum password length |
| `NEXUSAI_ENT_BACKEND` | `memory` | Persistence backend selector |
| `NEXUSAI_ENT_DATABASE_URL` | *(none)* | DSN for a durable backend |
| `NEXUSAI_ENT_KEY_PREFIX` | `hk` | API-key prefix |

## Scheduler

`NEXUSAI_SCHED_` prefix.

| Variable | Default | Purpose |
|---|---|---|
| `NEXUSAI_SCHED_WORKERS` | `2` | Worker-pool size |
| `NEXUSAI_SCHED_TICK` | `1.0` | Tick interval (seconds) |
| `NEXUSAI_SCHED_HISTORY` | `500` | In-memory run-history cap |
| `NEXUSAI_SCHED_WEBHOOK` | *(none)* | Webhook URL for notifications |

## Desktop

| Variable | Default | Purpose |
|---|---|---|
| `NEXUSAI_SPAWN_BACKEND` | `false` | Launch a local backend sidecar |
| `NEXUSAI_BACKEND_CMD` | `uvicorn` | Sidecar command |
| `NEXUSAI_BACKEND_ARGS` | `nexusai_pro_api.main:app …` | Sidecar arguments |
| `NEXUSAI_BACKEND_URL` | `http://127.0.0.1:8000` | Backend URL the app connects to |
| `NEXUSAI_RENDERER_URL` | `http://localhost:5173` | Dev renderer URL |
| `NEXUSAI_CRASH_URL` | *(none)* | Optional crash-upload endpoint |

## Release

| Variable | Default | Purpose |
|---|---|---|
| `RELEASE_CHANNEL` | `stable` | Release channel: `stable`, `beta`, `alpha` |
