# Audit Readiness (Headless-First)

TrustOps audit readiness is exposed through **`GET /api/v1/platform/audit-readiness`**
for headless consumers (CI, agents, runbooks) and the **`/console/audit-room/`**
console for human GRC leads and auditors. Both surfaces read the same payload.

See [HEADLESS_GRC.md](HEADLESS_GRC.md) for the overall architecture.

## Executive summary

| Dimension                     | TrustOps v0.2.x                                            |
| ----------------------------- | ---------------------------------------------------------- |
| Continuous control monitoring | Deterministic tests over customer lake                     |
| Framework packs               | SOC 2, NIST AI RMF, FedRAMP foundation, CIS AWS, ISO packs |
| Evidence automation           | Open connector catalog + read-only cloud posture           |
| Auditor experience            | Trust-center shares + `auditor` role redaction             |
| Access reviews                | Access-review campaigns with certify/revoke/flag           |
| Policy management             | Template library + employee acknowledgment on publish      |
| Point-in-time audit           | Assessment snapshots + hash chain                          |
| Personnel / HRIS              | Gap — use IdP + access reviews                             |
| Vendor risk                   | MVP vendor risk module + audit-room diligence rollups      |
| Workflow automation           | Native workflow canvas with approvals                      |
| Self-host / data residency    | **Yes** — core differentiator                              |
| Headless / agent API          | **Yes** — MCP, OpenAPI, agent harness, CI gates            |

## Workflow checklist

### Shipped (audit-ready today)

1. **Connect sources** — AWS/Azure/GCP/Snowflake/GitHub/Okta connectors with probe + sync health
2. **Map frameworks** — Register packs; dashboard framework readiness bars
3. **Run control tests** — Gold `control_tests.jsonl`; pass/fail on dashboard and controls pages
4. **Track violations** — Open findings with severity, owner guidance, remediation tasks
5. **Request evidence** — Evidence-request workflow tied to controls
6. **Access reviews** — Periodic certification campaigns (SOC 2 CC6.x pattern)
7. **Policies** — Adopt/publish from bundled templates
8. **Auditor sharing** — Scoped trust-center tokens with expiry and revocation
9. **Point-in-time** — Write assessment snapshot; ledger chain for drift detection
10. **Audit log** — Request audit trail for API and console actions
11. **Headless gates** — API keys, correlation IDs, idempotency for CI and agents

### Known gaps

| Gap                    | Workaround today                           |
| ---------------------- | ------------------------------------------ |
| Personnel tracking     | IdP connector + access reviews             |
| Auditor marketplace    | Export trust share + PDF snapshot          |
| Pen test coordination  | External process                           |
| Device/agent inventory | Connector evidence only                    |
| Policy acknowledgment  | Employee attestation on published policies |
| Native billing/signup  | Commercial scaffold (P5)                   |

## UI/UX targets (Epic #96)

| Surface              | Target                                                |
| -------------------- | ----------------------------------------------------- |
| Trust Home dashboard | Executive KPIs + audit strip + live posture           |
| Audit room           | Single pane for audit score, gaps, workflow checklist |
| Framework drill-down | Control → rule → evidence → datasource (#91)          |
| Dark mode            | CSS-variable theming across shell + review pages      |
| Workflow canvas      | Inspector + approvals (#90)                           |

## Audit score formula

The audit-readiness API computes:

```text
audit_score =
  40% posture score
+ 30% control test pass rate
+ 20% framework readiness (≥85% threshold)
+ 10% workflow coverage checklist
```

State:

- `audit_ready` — score ≥ 85 and no blocking gaps
- `on_track` — score ≥ 60
- `needs_work` — otherwise

Blocking gaps include: no connectors, failing controls, open evidence requests, no active access review, no auditor share, overdue or missing vendor diligence.

## Related

- [PRODUCT_SHAPE.md](PRODUCT_SHAPE.md) — parity map, open issues, execution order
- [HEADLESS_GRC.md](HEADLESS_GRC.md)
- [RELEASE_READINESS.md](RELEASE_READINESS.md)
- [DEPLOYMENT_AND_PRICING.md](DEPLOYMENT_AND_PRICING.md)
- Epic [#96](https://github.com/msaad00/trustops-security-data-lake/issues/96)
