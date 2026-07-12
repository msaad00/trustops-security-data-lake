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

Optional SCIM bearer provisioning (Enterprise tier; soft-deletes users on `DELETE`):

```bash
export TRUSTOPS_SCIM_ENABLED=1
export TRUSTOPS_SCIM_BEARER_TOKEN=<operator-issued-secret>
export TRUSTOPS_SCIM_TENANT_SLUG=<tenant-slug>   # defaults to TRUSTOPS_OIDC_TENANT_SLUG or "default"
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

| Method | Path                       | Auth                                | Description                |
| ------ | -------------------------- | ----------------------------------- | -------------------------- |
| `GET`  | `/api/v1/platform/pricing` | none                                | Tier list + limits (gated) |
| `POST` | `/api/v1/signup`           | optional `X-TrustOps-Signup-Secret` | Create tenant + admin user |
| `GET`  | `/api/v1/platform/usage`   | `auth_admin`                        | Plan tier, usage vs limits |

These routes return **501 Not Implemented** unless `TRUSTOPS_COMMERCIAL_HOSTED=1`.
Tier definitions and dollar amounts are operator-managed and not published in the
OSS repository or console.

## Email delivery

| `TRUSTOPS_EMAIL_PROVIDER` | Behavior                                                       |
| ------------------------- | -------------------------------------------------------------- |
| `log` (default)           | Log `{to, subject}` at INFO — safe for dev                     |
| other                     | Extend `security_lakehouse.commercial.email` with SES/SendGrid |

## SCIM

| Method   | Path                                    | When disabled | When enabled                                       |
| -------- | --------------------------------------- | ------------- | -------------------------------------------------- |
| `GET`    | `/api/v1/platform/scim`                 | config stub   | `enabled: true`                                    |
| `GET`    | `/api/v1/scim/v2/ServiceProviderConfig` | **501**       | patch supported; bearer auth                       |
| `GET`    | `/api/v1/scim/v2/Users`                 | **501**       | list tenant users (paginated)                      |
| `POST`   | `/api/v1/scim/v2/Users`                 | **501**       | create user (`userName`, `trustopsRole`, `active`) |
| `GET`    | `/api/v1/scim/v2/Users/{user_id}`       | **501**       | fetch single user                                  |
| `PATCH`  | `/api/v1/scim/v2/Users/{user_id}`       | **501**       | update `active` / `trustopsRole`                   |
| `DELETE` | `/api/v1/scim/v2/Users/{user_id}`       | **501**       | soft offboard (`is_active=false`, **204**)         |

All `/api/v1/scim/v2/*` routes require `Authorization: Bearer <TRUSTOPS_SCIM_BEARER_TOKEN>`.

## Database

Migration `0012_tenant_invites` adds the `tenant_invites` table.
Migration `0013_tenant_plan_tier` adds `tenants.plan_tier` for hosted limits.

```bash
security-lakehouse db migrate --lake build/lakehouse
```

## Related docs

- [Deployment](DEPLOYMENT.md) — OSS vs self-hosted positioning
- [HA read replicas](../runbooks/HA_READ_REPLICAS.md) — single-writer lake + read replicas
- [Helm security guards](../deploy/README.md) — auth + replica guards
