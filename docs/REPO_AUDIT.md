# Public Repository Audit

TrustOps can audit a public GitHub repository without a token and emit raw
evidence JSONL that can be routed into the security data lake.

```bash
security-lakehouse repo audit https://github.com/OWNER/REPO --out build/repo-audit.jsonl
security-lakehouse validate --raw build/repo-audit.jsonl
```

The public path collects only signals GitHub exposes without credentials:

| Signal               | Evidence                                                                                    |
| -------------------- | ------------------------------------------------------------------------------------------- |
| metadata             | visibility, default branch, archive/fork state, license, topics, languages, recent activity |
| code ownership       | `CODEOWNERS` locations when present                                                         |
| security policy      | `SECURITY.md` locations when present                                                        |
| CI workflows         | `.github/workflows/*.yml` and `.yaml` files                                                 |
| dependency manifests | package, Python, Go, Rust, Java, Ruby, and lockfile manifests                               |
| container/IaC        | Dockerfiles, Terraform, Helm, and Kustomize indicators                                      |
| AI artifacts         | model cards, eval files, prompt files, model directories                                    |
| code graph           | repository, top-level directories, languages, and evidence-signal graph                     |

Each record includes a stable `event_id`, `evidence_id`, `evidence_ref`,
`evidence_collected_at`, and SHA-256 hash. File excerpts are short and
secret-like values are redacted before they are written.

## Public Limits

Public unauthenticated mode does not guess private or organization-scoped
settings. It emits a `repository.authenticated_signal_gap` record with
`status=requires_authenticated_connector` for signals such as:

- branch protection rules
- secret scanning status
- Dependabot alerts
- code scanning alerts
- repository rulesets
- organization code-owner review rules

Use the authenticated GitHub/GitLab connector path for those controls. The
public audit is still useful for fast demos, OSS posture checks, and initial
repo inventory before requesting credentials.

Run the authenticated governance connector when those gaps matter:

```bash
TRUSTOPS_GITHUB_APP_INSTALLATION_TOKEN=... security-lakehouse repo governance-sync OWNER/REPO --out build/repo-governance.jsonl
security-lakehouse validate --raw build/repo-governance.jsonl
```

See [Repository Governance Connector](REPO_GOVERNANCE_CONNECTOR.md).
