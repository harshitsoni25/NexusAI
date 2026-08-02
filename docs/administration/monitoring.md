# Monitoring & Access

Operating a Nexus AI deployment: observing its health, and administering access for
multi-tenant installations.

## Health & readiness

```bash
nexusai doctor                    # CLI readiness checks
```

The REST API exposes liveness and readiness endpoints for orchestrator probes:

- Liveness: `GET /api/v1/health`
- Readiness: `GET /api/v1/health/ready`

## Structured logs

Logs are structured and correlated. Every line carries a correlation id; the REST API adds
a `request_id` (and `X-Request-ID` header) so a client action traces to its server logs.
Enable durable JSON logs with `NEXUSAI_LOGGING__FILE__ENABLED=true` and ship them to
your log platform.

## Audit trail

The enterprise layer records an append-only audit entry for every security- and
data-relevant action (who, what, when, target). Query it per workspace:

```bash
GET /api/enterprise/audit?action=&limit=100      # requires audit-read permission
```

Export the audit log to your SIEM on a schedule for retention.

## Crash reporting

The desktop app writes native crash dumps and a JSON error log under
`…/Nexus AI/crashes/`. Set `NEXUSAI_CRASH_URL` to forward crashes to a collector.

## Access administration (enterprise)

Multi-tenant deployments administer identity and access through the enterprise API:

- **Workspaces** — the tenant boundary; creating one seeds built-in roles and an owner.
- **Users & roles** — RBAC with built-in `owner`, `admin`, `member` and `viewer`, plus
  custom roles per workspace.
- **API keys** — created with the plaintext shown once; stored only as a hash; revocable.
- **Projects & teams** — group work and grant access collectively.

Every mutating action is permission-guarded and recorded in the audit trail. Grant
least-privilege roles and rotate API keys on personnel changes.
