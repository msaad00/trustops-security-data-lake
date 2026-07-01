# Mockup company fixtures

Synthetic-but-realistic evidence sets you can pipe through the lake to demo
the workbench without standing up real connectors.

Each company directory ships a `raw/security_events.jsonl` shaped exactly
like real connector output. Load one with the CLI:

```bash
security-lakehouse fixtures list
security-lakehouse fixtures load --company golden --out build/lakehouse
security-lakehouse serve --lake build/lakehouse
```

The shipped companies are:

| Company      | Profile                                                                                                   |
| ------------ | --------------------------------------------------------------------------------------------------------- |
| `golden`     | **Canonical demo** — all 33 SOC 2 common criteria + 4 NIST AI RMF controls (37 total) on the dashboard.   |
| `saas`       | Mid-size SaaS company — typical SOC 2 surface (IAM, GitHub, AWS, Okta, Jira).                             |
| `ai_lab`     | AI/ML lab — model registry + runtime inference + MCP server evidence in addition to the SaaS baseline.    |
| `fintech`    | Payments + ledger workload — KMS keys, audit log retention, payments egress controls, dependency scanner. |
| `healthcare` | Care + AI triage workload — PHI buckets, FHIR runtime gateway, model lineage, runtime PHI redaction.      |

Add a new company by dropping a directory with `raw/security_events.jsonl`
(must reference only control IDs that exist in `controls/catalog.json`).
