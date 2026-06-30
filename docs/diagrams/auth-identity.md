# Identity & Auth Boundary

TrustOps server mode uses one identity model for browser SSO and headless API
keys — the same tenant, role, scope, and audit envelope.

## Identity flow

```mermaid
flowchart LR
  subgraph IdP["Company identity"]
    OIDC["OIDC<br/>Okta / Entra / Google"]
    SAML["SAML 2.0"]
  end

  subgraph Headless["Automation"]
    KEY["API key<br/>agents / CI / MCP"]
  end

  subgraph TrustOps["TrustOps auth core"]
    MAP["Map email → user"]
    TEN["Tenant scope"]
    RBAC["Role + scopes"]
    SESS["Session / key hash"]
    AUD["Request audit log"]
  end

  subgraph Apps["Protected surfaces"]
    CON["Console"]
    V1["/api/v1"]
  end

  OIDC --> MAP
  SAML --> MAP
  KEY --> TEN
  MAP --> TEN --> RBAC --> SESS --> AUD
  RBAC --> CON
  RBAC --> V1
```

## OIDC vs SAML vs API key

| Method | Best for | TrustOps endpoints |
| ------ | -------- | ------------------ |
| **OIDC** | Modern IdPs (Okta, Entra ID, Google) | `GET /api/v1/auth/login` → callback |
| **SAML 2.0** | Enterprise IdPs without OIDC | `GET /api/v1/auth/saml/login` → ACS |
| **API key** | Agents, CI, MCP clients | `POST /api/v1/auth/keys` (admin) |

## Session contract

```mermaid
sequenceDiagram
  participant User as Human user
  participant IdP as Identity provider
  participant TO as TrustOps API
  participant DB as App state DB

  User->>TO: GET /api/v1/auth/login
  TO->>IdP: OAuth / SAML redirect
  IdP-->>User: Authenticate
  IdP-->>TO: Assertion / token
  TO->>DB: Resolve tenant user + role
  TO-->>User: HttpOnly session cookie
  User->>TO: Console / API (scoped)
  TO->>DB: Append audit event
```

## Roles (summary)

| Role | Typical access |
| ---- | -------------- |
| `admin` | Full platform + key admin |
| `security_admin` | Connectors, workflows, snapshots |
| `contributor` | Triage, evidence requests |
| `auditor` | Read-only + redaction |
| `read_only` | Internal read |

See [SERVER_AUTH.md](../SERVER_AUTH.md) and
[identity boundary SVG](../images/trustops-identity-boundary.svg).
