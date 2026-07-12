# TrustOps Roadmap

Prioritized enhancements from product audit (v0.2.0). Track in GitHub issues as needed.

## P0 — Shareable hosted demo (managed GRC-class entry)

- [x] Demo kit API (`demo_kit` on POC readiness) with copyable links
- [x] `/console/demo/` evaluator landing
- [x] Account-linking deep links (`/connectors/?connect=`)
- [x] First-run onboarding wizard (`/console/onboarding/`)
- [x] Hosted invite flow with email/SCIM (commercial SaaS)
- [x] One-click AWS/Azure/GCP cloud linking (OAuth-style / Terraform reader)

## P1 — Product depth

- [x] SOC 2 common criteria full pack (33 controls)
- [x] NIST AI RMF 1.0 full pack (72 subcategories)
- [x] FedRAMP Moderate foundation pack (287 NIST SP 800-53 Rev 5 controls)
- [x] CIS AWS Foundations v3.0 pack (62 recommendations)
- [x] ISO/IEC 27001:2022 and ISO/IEC 42001:2023 Annex A packs
- [x] `frameworks sync-packs` CLI + custom framework examples
- [x] Framework packs (SOC 2 Availability/Confidentiality/PI/Privacy TSC extensions)
- [x] Unified golden fixture (all 37 controls on dashboard)
- [x] Audit-scale synthetic data + streaming IO + capped violation rollups (`docs/AUDIT_SCALE.md`)
- [x] Executive PDF export from snapshots
- [x] Vendor risk questionnaire MVP
- [x] Policy template library MVP (bundled templates + adopt/publish)

## P2 — Agent-native moat

- [x] LangGraph for SOC triage harness
- [x] GitHub Action posture gate
- [x] MCP cookbook for evidence requests + approvals
- [x] Workflow operating loop (run inspector, dry-run preview, approval gate, retries)

## P3 — Operations

- [x] Backup/restore runbook for `/lake` + app DB
- [x] OpenTelemetry dashboards for connector sync
- [x] Helm guard: block insecure auth without explicit override
- [x] HA guidance (read replicas + single writer)

## P4 — Documentation & design

- [x] Shareable demo guide
- [x] Markdown image CI validation
- [x] OSS / self-hosted / hosted positioning (`docs/DEPLOYMENT.md`)
- [x] Console `/deploy` deployment summary page
- [x] Connector + auth flow diagrams (mermaid, SVG, console strips)
- [x] Commit demo PNG screenshots (`make demo-screenshots`)
- [x] Unified data model single-page diagram
- [x] Dark mode

## P5 — Commercial hosted

- [x] Commercial pricing API scaffold (gated env; not in OSS console)
- [x] Self-serve signup and tenant lifecycle
- [x] Usage limits enforcement scaffold
- [ ] Billing (Stripe) and SCIM provisioning

## P6 — Headless GRC

- [x] Headless architecture guide (`docs/HEADLESS_GRC.md`)
- [x] Unified v1 audit-log with stable event IDs (#339)
- [x] Audit readiness API and audit room (#340)
- [x] MCP/API resource catalog parity for platform endpoints (access reviews, policies, vendor diligence, insights)

## P7 — Turnkey GRC loop + premium UX (open)

Honest parity map: [PRODUCT_SHAPE.md](docs/PRODUCT_SHAPE.md)

| Issue                                                                                                                                             | Closes                                                                       |
| ------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| [#96](https://github.com/msaad00/trustops-security-data-lake/issues/96)                                                                           | Premium GRC SaaS UX — design system, Trust Home, workflow canvas, drill-down |
| [#13](https://github.com/msaad00/trustops-security-data-lake/issues/13)                                                                           | Evidence freshness SLA + stale evidence → remediation                        |
| [#15](https://github.com/msaad00/trustops-security-data-lake/issues/15) / [#18](https://github.com/msaad00/trustops-security-data-lake/issues/18) | Audit room trends + product-grade visualizations                             |
| [#22](https://github.com/msaad00/trustops-security-data-lake/issues/22) / [#23](https://github.com/msaad00/trustops-security-data-lake/issues/23) | GitHub/GitLab governance + repo graph workbench                              |
| [#14](https://github.com/msaad00/trustops-security-data-lake/issues/14)                                                                           | Source-linked framework/control expansion                                    |
| [#345](https://github.com/msaad00/trustops-security-data-lake/pull/345)                                                                           | Identity/admin parity (users, API-key session, IdP roles, SCIM scaffold)     |

See [TRUSTOPS_85_PLAN.md](docs/TRUSTOPS_85_PLAN.md) for the 85% self-hosted bar.
