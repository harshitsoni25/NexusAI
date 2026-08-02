# Troubleshooting

!!! tip "Before you start"
    Note your version (`nexusai version`, or Desktop → **Help → About**) and the
    relevant `request_id` from the logs — both speed up diagnosis.

## `nexusai doctor` reports a failure

Run `nexusai doctor` and address each failing check. Common causes are a missing data
root (create it or set `NEXUSAI_PATHS__ROOT`) or a plugin that fails to load.

## A plugin isn't loaded

- List plugins with `nexusai plugins` — rejected plugins show a reason.
- Confirm the distribution exposes a `nexusai.plugins` entry point.
- Check the plugin's declared API version is compatible with the framework.

## The web UI can't reach the backend

- Confirm the API is running: `GET http://127.0.0.1:8000/api/v1/health`.
- If the top bar shows **Mock data**, set `VITE_USE_MOCKS=false` and restart.

## `401 Unauthorized` from the enterprise API

- Your token may have expired (`NEXUSAI_ENT_TOKEN_TTL`). Log in again.
- For machine calls, send the key as `X-API-Key`, not as a bearer token.

## `403 Forbidden`

- The principal lacks the required permission. Review the user's roles in the
  [enterprise administration](../administration/monitoring.md) surface.

## The desktop app won't open (macOS)

- Signed, notarised builds open normally. For a local unsigned build, right-click →
  **Open** the first time.

## Finding crash logs (desktop)

Native crash dumps and a JSON error log are written under `…/Nexus AI/crashes/`. Attach
these when filing an issue.

Still stuck? See [Support](https://github.com/nexusai/nexusai/blob/main/SUPPORT.md).
