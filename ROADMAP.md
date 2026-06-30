# TrustOps Roadmap

Prioritized enhancements from product audit (v0.2.0). Track in GitHub issues as needed.

## P0 — Shareable hosted demo (Drata/Vanta-class entry)

- [x] Demo kit API (`demo_kit` on POC readiness) with copyable links
- [x] `/console/demo/` evaluator landing
- [x] Account-linking deep links (`/connectors/?connect=`)
- [ ] Hosted invite flow with email/SCIM (commercial SaaS)
- [ ] One-click AWS/Azure consent (OAuth-style cloud linking)

## P1 — Product depth

- [ ] Framework packs (SOC 2 50+, ISO Annex A starter)
- [ ] Unified golden fixture (all 37 controls on dashboard)
- [ ] Executive PDF export from snapshots
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
- [ ] Commit demo PNG screenshots (`make demo-screenshots`)
- [ ] Unified data model single-page diagram
- [ ] Dark mode

See [TRUSTOPS_85_PLAN.md](docs/TRUSTOPS_85_PLAN.md) for the 85% self-hosted bar.
