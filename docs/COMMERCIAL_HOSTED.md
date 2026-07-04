# Commercial Hosted Features

TrustOps OSS/self-hosted builds include **scaffolding** for managed SaaS capabilities:
tenant email invites, outbound mail adapters, and SCIM 2.0 provisioning hooks.

Full Stripe/invoicing billing is operator-managed in v0.2.x; this doc covers
pricing tiers, self-serve signup scaffold, usage limits, invites, email, and SCIM hooks.

## Enable hosted mode

```bash
export TRUSTOPS_COMMERCIAL_HOSTED=1
export TRUSTOPS_PUBLIC_URL=https://trustops.example.com
export TRUSTOPS_EMAIL_PROVIDER=log   # default: log-only (no SMTP)
```

Self-serve workspace creation:

```bash
export TRUSTOPS_SELF_SERVE_SIGNUP=1
export TRUSTOPS_SIGNUP_SECRET=<optional-abuse-guard>
```

Optional SCIM (returns empty collections when enabled; full provisioning in managed SaaS):

```bash
export TRUSTOPS_SCIM_ENABLED=1
export TRUSTOPS_SCIM_BEARER_TOKEN=<operator-issued-secret>
```

## Invite API

| Method | Path                     | Auth              | Description                |
| ------ | ------------------------ | ----------------- | -------------------------- |
| `GET`  | `/api/v1/invites`        | `auth_admin`      | List tenant invites        |
| `POST` | `/api/v1/invites`        | `auth_admin`      | Create invite + send email |
| `POST` | `/api/v1/invites/accept` | none (token body) | Accept pending invite      |

Create body:

```json
{ "email": "user@company.com", "role": "contributor" }
```

Accept body:

```json
{ "token": "<invite-token-from-email>", "display_name": "Alex" }
```

When `TRUSTOPS_COMMERCIAL_HOSTED` is unset, invite routes return **501 Not Implemented**.

## Pricing and signup

| Method | Path                       | Auth                                | Description                  |
| ------ | -------------------------- | ----------------------------------- | ---------------------------- |
| `GET`  | `/api/v1/platform/pricing` | none                                | Published tier list + limits |
| `POST` | `/api/v1/signup`           | optional `X-TrustOps-Signup-Secret` | Create tenant + admin user   |
| `GET`  | `/api/v1/platform/usage`   | `auth_admin`                        | Plan tier, usage vs limits   |

See [HOSTED_PRICING.md](HOSTED_PRICING.md) for tier details and console `/console/pricing/`.

## Email delivery

| `TRUSTOPS_EMAIL_PROVIDER` | Behavior                                                       |
| ------------------------- | -------------------------------------------------------------- |
| `log` (default)           | Log `{to, subject}` at INFO — safe for dev                     |
| other                     | Extend `security_lakehouse.commercial.email` with SES/SendGrid |

## SCIM

| Method     | Path                    | When disabled | When enabled                            |
| ---------- | ----------------------- | ------------- | --------------------------------------- |
| `GET`      | `/api/v1/platform/scim` | config stub   | `enabled: true`                         |
| `GET/POST` | `/api/v1/scim/v2/*`     | **501**       | empty Users list (managed SaaS extends) |

## Database

Migration `0012_tenant_invites` adds the `tenant_invites` table.
Migration `0013_tenant_plan_tier` adds `tenants.plan_tier` for hosted limits.

```bash
security-lakehouse db migrate --lake build/lakehouse
```

## Related docs

- [Hosted pricing tiers](HOSTED_PRICING.md)

- [HA read replicas](../runbooks/HA_READ_REPLICAS.md) — single-writer lake + read replicas
- [Deployment and pricing](DEPLOYMENT_AND_PRICING.md) — OSS vs hosted positioning
- [Helm security guards](../deploy/README.md) — auth + replica guards
