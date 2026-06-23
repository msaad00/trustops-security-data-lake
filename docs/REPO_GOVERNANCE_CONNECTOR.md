# Repository Governance Connector

TrustOps can sync authenticated GitHub repository governance evidence for
private repos and organization-only controls that public audit cannot observe.
The connector emits raw JSONL evidence that can be validated and routed into
the security data lake.

```bash
TRUSTOPS_GITHUB_APP_INSTALLATION_TOKEN=... security-lakehouse repo governance-sync OWNER/REPO --out build/repo-governance.jsonl
security-lakehouse validate --raw build/repo-governance.jsonl
```

Offline fixture mode is available for tests, demos, and CI without credentials:

```bash
security-lakehouse repo governance-sync OWNER/REPO \
  --fixture-dir tests/fixtures/github-governance \
  --out build/repo-governance.jsonl
```

## Access Boundary

Use a GitHub App installation token with read-only repository permissions. The
connector does not need write, delete, admin, secret value, or package publish
permissions.

| Scope or permission    | Unlocks                                                            |
| ---------------------- | ------------------------------------------------------------------ |
| `metadata:read`        | repository identity, default branch, visibility, source health     |
| `contents:read`        | repo-level metadata needed to link evidence to the repo asset      |
| `administration:read`  | branch protection, collaborators, teams, workflow permissions      |
| `security_events:read` | security setting and alert availability summaries where allowed    |
| fixture bundle         | deterministic local evidence with `credential_fingerprint=fixture` |

Installation token values are never emitted. TrustOps stores only a short
SHA-256 credential fingerprint so operators can tell which credential boundary
produced evidence without exposing the credential itself.

## Evidence Signals

| Event type                                   | Why it matters                                     |
| -------------------------------------------- | -------------------------------------------------- |
| `repository.governance.branch_protection`    | required reviews, status checks, admin enforcement |
| `repository.governance.collaborators`        | direct user access and role inventory              |
| `repository.governance.teams`                | team-based maintainers and approver boundaries     |
| `repository.governance.workflow_permissions` | GitHub Actions default token behavior              |
| `repository.governance.security_settings`    | security alert availability where the API permits  |

Each emitted record includes:

- `event_id`
- `tenant_id`
- `workspace_id`
- `event_time`
- `source=github-repo-governance`
- `event_type`
- `entity.asset_id`
- `entity.asset_type=repository`
- `entity.repo`
- `controls`
- `evidence.evidence_id`
- `evidence.evidence_ref`
- `evidence.evidence_collected_at`
- `evidence.raw_sha256`
- `attributes.source_health`

The connector collects evidence only. Compliance posture is still evaluated by
the assessment engine from normalized facts, mappings, freshness, and control
rules.

## Relationship To Public Audit

Use `security-lakehouse repo audit` first for fast public inventory and code
graph evidence. Use `security-lakehouse repo governance-sync` when a control
depends on private or organization-scoped GitHub settings.

Public audit emits `repository.authenticated_signal_gap` when it reaches a
signal that needs authenticated access. Governance sync closes that gap with
provable evidence instead of guessing.
