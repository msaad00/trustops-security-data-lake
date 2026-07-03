# Commercial Hosted Features

TrustOps OSS/self-hosted builds include **scaffolding** for managed SaaS capabilities:
tenant email invites, outbound mail adapters, and SCIM 2.0 provisioning hooks.

Full billing, self-serve signup, and production SCIM are commercial-only; enable the
scaffold locally to validate integration contracts before a hosted rollout.

## Enable hosted mode

```bash
export TRUSTOPS_COMMERCIAL_HOSTED=1
export TRUSTOPS_PUBLIC_URL=https://trustops.example.com
export TRUSTOPS_EMAIL_PROVIDER=log   # default: log-only (no SMTP)
```

Optional SCIM (returns empty collections when enabled; full provisioning in managed SaaS):

```bash
export TRUSTOPS_SCIM_ENABLED=1
export TRUSTOPS_SCIM_BEARER_TOKEN=<operator-issued-secret>
```

## Invite API

| Method | Path | Auth | Description |
| ------ | ---- | ---- | ----------- |
| `GET` | `/api/v1/invites` | `auth_admin` | List tenant invites |
| `POST` | `/api/v1/invites` | `auth_admin` | Create invite + send email |
| `POST` | `/api/v1/invites/accept` | none (token body) | Accept pending invite |

Create body:

```json
{ "email": "user@company.com", "role": "contributor" }
```

Accept body:

```json
{ "token": "<invite-token-from-email>", "display_name": "Alex" }
```

When `TRUSTOPS_COMMERCIAL_HOSTED` is unset, invite routes return **501 Not Implemented**.

## Email delivery

| `TRUSTOPS_EMAIL_PROVIDER` | Behavior |
| ------------------------- | -------- |
| `log` (default) | Log `{to, subject}` at INFO — safe for dev |
| other | Extend `security_lakehouse.commercial.email` with SES/SendGrid |

## SCIM

| Method | Path | When disabled | When enabled |
| ------ | ---- | ------------- | ------------ |
| `GET` | `/api/v1/platform/scim` | config stub | `enabled: true` |
| `GET/POST` | `/api/v1/scim/v2/*` | **501** | empty Users list (managed SaaS extends) |

## Database

Migration `0012_tenant_invites` adds the `tenant_invites` table. Run:

```bash
security-lakehouse db migrate --lake build/lakehouse
```

## Related docs

- [HA read replicas](../runbooks/HA_READ_REPLICAS.md) — single-writer lake + read replicas
- [Deployment and pricing](DEPLOYMENT_AND_PRICING.md) — OSS vs hosted positioning
- [Helm security guards](../deploy/README.md) — auth + replica guards
