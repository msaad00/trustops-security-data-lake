# Competitive Audit Parity (Vanta / Drata)

Fresh audit of TrustOps v0.2.x against the **audit-center workflow** that
managed GRC platforms (Vanta, Drata, Secureframe, etc.) optimize for — not a
marketing claim of feature parity.

## Executive summary

| Dimension | Vanta / Drata | TrustOps v0.2.x |
| --------- | ------------- | --------------- |
| Continuous control monitoring | Native tests + integrations | Deterministic tests over customer lake |
| Framework packs | Broad, sales-curated | SOC 2, NIST AI RMF, FedRAMP foundation, CIS AWS, ISO packs |
| Evidence automation | Deep integration marketplace | Open connector catalog + read-only cloud posture |
| Auditor experience | Hosted auditor portal | Trust-center shares + `auditor` role redaction |
| Access reviews | Personnel + app access | Access-review campaigns with certify/revoke/flag |
| Policy management | Large template library | MVP template library (8 templates) |
| Point-in-time audit | Audit period snapshots | Assessment snapshots + hash chain |
| Personnel / HRIS | Native | Gap — use IdP + access reviews |
| Vendor risk | Mature questionnaires | MVP vendor risk module |
| Workflow automation | Limited native | Tines-grade workflow canvas (differentiator) |
| Self-host / data residency | No | **Yes** — core differentiator |
| Headless / agent API | Limited | **Yes** — MCP, OpenAPI, agent harness |

**Console surface:** `/console/audit-room/` aggregates audit score, gaps, and parity checklist.
**API:** `GET /api/v1/platform/audit-readiness`

## Workflow parity checklist

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

### Gaps (honest)

| Gap | Vanta/Drata | TrustOps workaround |
| --- | ----------- | ------------------- |
| Personnel tracking | HRIS-linked onboarding | IdP connector + access reviews |
| Auditor marketplace | In-product auditor network | Export trust share + PDF snapshot |
| Pen test coordination | In-app | External process |
| Device/agent inventory | Endpoint agents | Connector evidence only |
| Policy acknowledgment | Employee attestation flows | Roadmap |
| Native billing/signup | Self-serve SaaS | Commercial scaffold (P5) |

## UI/UX parity targets (Epic #96)

| Surface | Target bar |
| ------- | ---------- |
| Trust Home dashboard | Executive KPIs + audit strip + live posture |
| Audit room | Single pane for audit score, gaps, parity checklist |
| Framework drill-down | Control → rule → evidence → datasource (#91) |
| Dark mode | CSS-variable theming across shell + review pages |
| Workflow canvas | Tines-grade inspector + approvals (#90) |

## Audit score formula

The audit-readiness API computes:

```text
audit_score =
  40% posture score
+ 30% control test pass rate
+ 20% framework readiness (≥85% threshold)
+ 10% workflow parity checklist
```

State:

- `audit_ready` — score ≥ 85 and no blocking gaps
- `on_track` — score ≥ 60
- `needs_work` — otherwise

Blocking gaps include: no connectors, failing controls, open evidence requests, no active access review, no auditor share.

## Related

- [RELEASE_READINESS.md](RELEASE_READINESS.md)
- [DEPLOYMENT_AND_PRICING.md](DEPLOYMENT_AND_PRICING.md)
- Epic [#96](https://github.com/msaad00/trustops-security-data-lake/issues/96)
