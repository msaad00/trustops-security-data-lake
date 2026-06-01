# Server Auth

TrustOps server mode has one identity model:

```text
API key, OIDC login, or SAML login
  -> user
  -> tenant
  -> role
  -> RBAC scopes
  -> request audit event
```

Local mode stays zero-dependency. These settings apply only when running the
FastAPI server surface from `trustops-security-data-lake[server]`.

## API Keys

API keys are for agents, CI, and service accounts. The database stores only a
SHA-256 token hash. Raw key material is returned once by the authenticated API
creation endpoint.

```bash
security-lakehouse platform seed-dev --lake build/lakehouse
security-lakehouse auth list-keys --lake build/lakehouse --tenant-slug acme
```

## OIDC

OIDC is the preferred human-login path when the company identity provider
supports it.

```bash
export TRUSTOPS_OIDC_ISSUER="https://idp.example.com"
export TRUSTOPS_OIDC_CLIENT_ID="trustops"
export TRUSTOPS_OIDC_CLIENT_SECRET="..."
export TRUSTOPS_OIDC_TENANT_SLUG="acme"
export TRUSTOPS_OIDC_AUTO_PROVISION="false"
export TRUSTOPS_SESSION_SECRET="replace-with-32-byte-random-secret"
```

Endpoints:

| Endpoint                    | Purpose                                           |
| --------------------------- | ------------------------------------------------- |
| `GET /api/v1/auth/methods`  | Discover configured browser login methods         |
| `GET /api/v1/auth/login`    | Start OIDC login                                  |
| `GET /api/v1/auth/callback` | Complete OIDC login and issue the browser session |
| `POST /api/v1/auth/logout`  | Revoke the browser session                        |

## SAML

SAML is the enterprise fallback for identity providers that do not expose OIDC
to the TrustOps deployment. It resolves into the same browser session and RBAC
context as OIDC.

```bash
export TRUSTOPS_SAML_SP_ENTITY_ID="https://trustops.example.com/api/v1/auth/saml/metadata"
export TRUSTOPS_SAML_ACS_URL="https://trustops.example.com/api/v1/auth/saml/acs"
export TRUSTOPS_SAML_IDP_ENTITY_ID="https://idp.example.com/saml"
export TRUSTOPS_SAML_IDP_SSO_URL="https://idp.example.com/saml/sso"
export TRUSTOPS_SAML_IDP_X509_CERT="-----BEGIN CERTIFICATE-----..."
export TRUSTOPS_SAML_TENANT_SLUG="acme"
export TRUSTOPS_SAML_AUTO_PROVISION="false"
```

Endpoints:

| Endpoint                         | Purpose                                                 |
| -------------------------------- | ------------------------------------------------------- |
| `GET /api/v1/auth/saml/login`    | Start SAML login                                        |
| `POST /api/v1/auth/saml/acs`     | Assertion consumer service; validates the SAML response |
| `GET /api/v1/auth/saml/metadata` | Service-provider metadata for identity-provider setup   |

If any SAML environment variable is present, all required SAML variables must
be present. The server fails closed instead of starting with a partial SSO
boundary.

## Roles

| Role             | Access                                                      |
| ---------------- | ----------------------------------------------------------- |
| `admin`          | Full access, including user and API key administration      |
| `security_admin` | Connector, workflow, snapshot, and control operations       |
| `contributor`    | Evidence request, workflow action, and triage operations    |
| `auditor`        | Read-only, with owner, credential, and note fields redacted |
| `read_only`      | Internal read-only view without mutation                    |

All non-health `/api/v1/*` and `/api/*` requests are authenticated in server
mode. Request audit events include a correlation ID, actor, tenant, route,
method, decision, status, and timestamp.

## Tenant data isolation

Server mode binds to a lake _root_. Each tenant's bronze/silver/gold evidence
lives under `<root>/tenants/<tenant_id>`, and every data route resolves its lake
from the authenticated identity, so one tenant can never read another tenant's
posture, controls, evidence, violations, or connector configuration.

A _flat_ lake written directly at the root — the layout the CLI `pipeline` and
`fixtures` commands produce — is served, for backward compatibility, only to a
single-tenant deployment (the sole tenant in the database) or to the synthetic
tenant of `--allow-insecure-no-auth` local mode. When a second tenant exists,
the flat root lake is bound to nobody: each tenant reads its own `tenants/<id>`
subtree (initially empty) rather than another tenant's data. Provision
per-tenant lakes by running the pipeline with `--out <root>/tenants/<tenant_id>`.

The bundled console redirects unauthenticated browser traffic to `/console/login`.
That page reads `GET /api/v1/auth/methods` and only enables login buttons for
configured OIDC or SAML providers. Agent and CI access should continue to use
API keys.
