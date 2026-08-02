# Roadmap

This roadmap describes planned work in the application layer. The certified engine remains
frozen; engine changes would require a separate re-certification and are out of scope for
application roadmap items.

## Near term

- **Durable persistence adapters** — SQL/NoSQL implementations of the enterprise
  repository ports and a durable scheduler store for multi-instance deployments.
- **Authentication hardening** — login rate-limiting and a password-reset flow.
- **Unified log schema** — a single structured JSON format across all services with a
  shipping preset.
- **Release attestation** — checksums and an SBOM in the release pipeline.

## Mid term

- **Live reporting metrics** — an opt-in metrics store so trends, execution time and
  storage series are live rather than illustrative.
- **Scheduler high availability** — leader election with schedules backed by the durable
  store.
- **Finer-grained authorization** — project- and team-scoped permission checks.
- **Plugin catalogue** — a curated browse-and-install experience over the existing plugin
  manager.

## Long term

- **SSO / SCIM** — OIDC/SAML login and directory synchronisation.
- **Managed cloud offering** — multi-region blueprint, autoscaling and usage metering.
- **Observability suite** — OpenTelemetry metrics and traces with a prebuilt dashboard.

## Out of scope

- Modifying the certified engine. Any engine change requires a new, separately certified
  revision.
