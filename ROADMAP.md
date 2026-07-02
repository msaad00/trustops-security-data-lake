# TrustOps Roadmap

Prioritized enhancements from product audit (v0.2.0). Track in GitHub issues as needed.

## P0 — Shareable hosted demo (managed GRC-class entry)

- [x] Demo kit API (`demo_kit` on POC readiness) with copyable links
- [x] `/console/demo/` evaluator landing
- [x] Account-linking deep links (`/connectors/?connect=`)
- [ ] Hosted invite flow with email/SCIM (commercial SaaS)
- [x] One-click AWS/Azure consent (OAuth-style cloud linking)

## P1 — Product depth

- [x] SOC 2 common criteria full pack (33 controls)
- [x] NIST AI RMF 1.0 full pack (72 subcategories)
- [x] FedRAMP Moderate foundation pack (287 NIST SP 800-53 Rev 5 controls)
- [x] CIS AWS Foundations v3.0 pack (62 recommendations)
- [x] ISO/IEC 27001:2022 and ISO/IEC 42001:2023 Annex A packs
- [x] `frameworks sync-packs` CLI + custom framework examples
- [ ] Framework packs (SOC 2 Availability/Confidentiality/PI/Privacy TSC extensions)
- [x] Unified golden fixture (all 37 controls on dashboard)
- [x] Executive PDF export from snapshots
- [ ] Vendor risk questionnaire MVP

## P2 — Agent-native moat

- [x] LangGraph for SOC triage harness
- [ ] GitHub Action posture gate
- [ ] MCP cookbook for evidence requests + approvals

## P3 — Operations

- [ ] Backup/restore runbook for `/lake` + app DB
- [ ] OpenTelemetry dashboards for connector sync
- [ ] Helm guard: block insecure auth without explicit override
- [ ] HA guidance (read replicas + single writer)

## P4 — Documentation & design

- [x] Shareable demo guide
- [x] Markdown image CI validation
- [x] OSS / self-hosted / hosted positioning (`docs/DEPLOYMENT_AND_PRICING.md`)
- [x] Console `/deploy` deployment summary page
- [x] Connector + auth flow diagrams (mermaid, SVG, console strips)
- [ ] Commit demo PNG screenshots (`make demo-screenshots`)
- [ ] Unified data model single-page diagram
- [ ] Dark mode

## P5 — Commercial hosted (future)

- [ ] Published hosted pricing tiers
- [ ] Self-serve signup and tenant lifecycle
- [ ] Billing, usage limits, and SCIM

See [TRUSTOPS_85_PLAN.md](docs/TRUSTOPS_85_PLAN.md) for the 85% self-hosted bar.
