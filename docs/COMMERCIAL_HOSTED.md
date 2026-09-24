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

Optional SCIM 2.0 provisioning (Enterprise tier). Enable it, then have a tenant
admin issue a SCIM token (see [SCIM](#scim)):

```bash
export TRUSTOPS_SCIM_ENABLED=1
# Optional: map IdP groups to TrustOps roles (highest privilege wins).
export TRUSTOPS_SCIM_ROLE_MAP='{"TrustOps Admins": "admin", "TrustOps Auditors": "auditor"}'
export TRUSTOPS_SCIM_DEFAULT_ROLE=read_only   # role for users in no mapped group
```

`TRUSTOPS_SCIM_BEARER_TOKEN` + `TRUSTOPS_SCIM_TENANT_SLUG` still authenticate as a
deprecated single-tenant fallback; prefer per-tenant tokens.

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

SCIM endpoints return raw SCIM JSON (`application/scim+json`, no TrustOps
envelope) and SCIM error objects (`urn:ietf:params:scim:api:messages:2.0:Error`
with `status` and, where relevant, `scimType`), which is what Okta and Entra ID
parse. Every `/api/v1/scim/v2/*` call except `ServiceProviderConfig` needs
`Authorization: Bearer <tenant SCIM token>`; the token selects the tenant, so a
token can never read or change another tenant's users or groups.

### Tokens (tenant admin, TrustOps API)

| Method   | Path                                | Description                                                 |
| -------- | ----------------------------------- | ----------------------------------------------------------- |
| `POST`   | `/api/v1/platform/scim/tokens`      | Issue a token (`{"name": "okta"}`); plaintext returned once |
| `GET`    | `/api/v1/platform/scim/tokens`      | List tokens: name, prefix, created, last used, revoked      |
| `DELETE` | `/api/v1/platform/scim/tokens/{id}` | Revoke                                                      |

Only a SHA-256 hash of each token is stored. Rotate by issuing a new token,
updating the IdP, then revoking the old one; both work until the revoke.

### Users and groups

| Method                       | Path                                    | Notes                                                                               |
| ---------------------------- | --------------------------------------- | ----------------------------------------------------------------------------------- |
| `GET`                        | `/api/v1/scim/v2/ServiceProviderConfig` | patch + filter supported; bulk, sort, etag, changePassword not                      |
| `GET`                        | `/api/v1/scim/v2/Users`                 | `filter=userName eq "…"` or `externalId eq "…"`; `startIndex`/`count` (max 200)     |
| `POST`                       | `/api/v1/scim/v2/Users`                 | `409 uniqueness` for an existing userName; re-creating a deleted user restores it   |
| `GET`/`PUT`/`PATCH`          | `/api/v1/scim/v2/Users/{id}`            | PATCH accepts path and path-less operations (Okta and Entra ID shapes)              |
| `DELETE`                     | `/api/v1/scim/v2/Users/{id}`            | Soft delete: deactivated, removed from groups, then 404 to SCIM; row kept for audit |
| `GET`/`POST`                 | `/api/v1/scim/v2/Groups`                | `filter=displayName eq "…"`; members must be users of the same tenant               |
| `GET`/`PUT`/`PATCH`/`DELETE` | `/api/v1/scim/v2/Groups/{id}`           | PATCH add/remove/replace `members`, including `members[value eq "…"]`               |

With `TRUSTOPS_SCIM_ROLE_MAP` set, every membership change recomputes the
affected users' roles: the highest-privilege mapped group wins, and a user in no
mapped group gets `TRUSTOPS_SCIM_DEFAULT_ROLE`. Without a role map, groups are
stored but never change roles. This has been tested against the RFC 7644 shapes
Okta and Entra ID send, not yet against a live IdP tenant.

## Database

Migration `0012_tenant_invites` adds the `tenant_invites` table.
Migration `0013_tenant_plan_tier` adds `tenants.plan_tier` for hosted limits.
Migration `0017_scim` adds `scim_tokens`, `scim_groups`, `scim_group_members`, and
`users.scim_external_id` / `users.scim_deleted_at`.

```bash
security-lakehouse db upgrade --lake build/lakehouse
```

## Related docs

- [Deployment](DEPLOYMENT.md) — OSS vs self-hosted positioning
- [HA read replicas](../runbooks/HA_READ_REPLICAS.md) — single-writer lake + read replicas
- [Helm security guards](../deploy/README.md) — auth + replica guards
