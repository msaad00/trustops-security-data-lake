# Pilot Roadmap Tracker

This tracker keeps the one-company internal TrustOps pilot honest. It maps the
remaining open roadmap issues to delivery phases, owner surfaces, acceptance
evidence, and sequencing. For the full product-shape parity map and recommended
PR execution order, see [PRODUCT_SHAPE.md](PRODUCT_SHAPE.md).

Status is intentionally conservative:

- **Shipped**: closed issue or merged PR with repo evidence.
- **Partial**: a working surface exists, but the open issue acceptance criteria
  are not complete.
- **Planned**: no complete pilot surface is shipped yet.

## Pilot Outcome

A pilot operator can run one command, ingest or audit repository/security
evidence, open the app, see current posture, triage failing controls, request or
track evidence, freeze a point-in-time snapshot, and query the same state
through agent-safe APIs.

Deferred until after pilot: broad framework expansion beyond source-linked
coverage, a full controls-as-code DSL, full SSO/SAML, production multi-tenant
SaaS posture, and enterprise connectors beyond the first repository/security
sources.

## Current Evidence Baseline

| Surface                        | Status  | Evidence                                                                                                                   |
| ------------------------------ | ------- | -------------------------------------------------------------------------------------------------------------------------- |
| CI quality gates and API smoke | Shipped | PR #20 merged.                                                                                                             |
| Versioned agent API contracts  | Shipped | #11 closed; `docs/api/AGENT_API.md`, `tests/test_api_v1.py`, and `/api/v1/*` routes in `src/security_lakehouse/server.py`. |
| Public repository audit        | Shipped | #21 closed; `docs/REPO_AUDIT.md`, `src/security_lakehouse/repo_audit.py`, and `tests/test_repo_audit.py`.                  |
| Product walkthrough            | Shipped | #17 closed; `docs/PRODUCT_WALKTHROUGH.md` separates shipped, partial, and planned capability claims.                       |
| Repository governance sync     | Partial | #22 remains open; PR #62 added GitHub governance sync, but GitLab and broader connector runner work remain issue-owned.    |
| React control-plane shell      | Partial | Open #9; `app/web/` exists, but role-aware production navigation and browser evidence remain issue-owned.                  |
| Evidence freshness workflow    | Partial | Open #13; freshness code/tests exist, but stale evidence enforcement and UI/agent workflow are not complete.               |
| Snapshot and trust sharing     | Partial | Open #15; snapshot API/CLI exists, but reviewer room and redaction-oriented reviewer mode remain planned.                  |

## Milestone Phases

| Phase                   | Goal                                                                                    | Issues           | Status  | Owner surfaces                                                                       | Acceptance evidence                                                                                                                                                                                            |
| ----------------------- | --------------------------------------------------------------------------------------- | ---------------- | ------- | ------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0. Baseline proof       | Keep the repo buildable and expose stable local contracts.                              | PR #20, #11, #21 | Shipped | CI, local CLI, `/api/v1`, public repo audit                                          | Green CI gates, `make smoke`, `tests/test_api_v1.py`, `tests/test_repo_audit.py`, `docs/REPO_AUDIT.md`.                                                                                                        |
| 1. Pilot boundary       | Make the internal deployment boundary explicit before more workflow claims.             | #10              | Shipped | API middleware, tenant/workspace model, audit events, local vs production mode docs  | Non-health endpoints reject anonymous traffic outside local mode; audit events include actor, tenant, route, decision, and correlation ID; docs explain fail-closed behavior.                                  |
| 2. Evidence ingestion   | Move from catalog contracts and public audit into first authenticated evidence sources. | #8, #22          | Partial | Connector runner, GitHub/GitLab governance connector, source health, redaction tests | `github-security` fixture runner; optional live credential smoke; normalized records with source, collected_at, evidence_ref, tenant/workspace, asset ID, hash; minimum-scope docs.                            |
| 3. Evaluation model     | Convert posture into reusable, freshness-aware control evaluation.                      | #7, #13, #14     | Partial | Policy/evaluation engine, framework registry, control catalog, freshness checks      | Deterministic evaluation tests; validation rejects unsupported controls/frameworks; stale evidence changes control outcomes; framework expansion remains source-linked and readiness-gated.                    |
| 4. Operator workbench   | Make the app usable for a pilot operator, not only a generated dashboard.               | #9, #18, #23     | Partial | React shell, graph workbench, topology/trend/SLA visuals, mobile/desktop UI          | API-backed pages; repository graph nodes/edges; visual links into controls, evidence, violations, and tasks; browser screenshots at desktop and mobile widths.                                                 |
| 5. Remediation workflow | Turn findings into owner work with evidence requests and exception tracking.            | #12              | Planned | Task records, evidence requests, owner queues, audit trail                           | Lifecycle states exist; control/violation views can create and update workflow records; SLA, owner, linked evidence, and audit trail are visible through UI and API.                                           |
| 6. Audit handoff        | Freeze and review pilot evidence without overstating certification status.              | #15, #17         | Partial | Snapshot room, reviewer trust center, README/product docs                            | Snapshot list/detail show reason, creator, hash, framework scope, posture, evidence refs, and export JSON; reviewer mode hides sensitive raw evidence by default; docs separate shipped, partial, and planned. |
| 7. Agent control plane  | Let humans and agents use the same guarded contracts.                                   | #16              | Partial | Agent page, skill registry, API examples, action audit events                        | Agent actions map to API routes and audit events; unsupported framework/control claims are rejected or marked unimplemented; fixture simulator covers analyst actions.                                         |

## Issue Tracker

| Issue                                       | Status  | Phase | Sequencing note                                                                                              | Acceptance evidence to attach before closing                                                           |
| ------------------------------------------- | ------- | ----- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| #10 Auth, tenants, RBAC, audit boundaries   | Shipped | 1     | API keys, OIDC, SAML, RBAC, request audit, and server-mode console API auth are in place.                    | Auth mode tests, audit event fixture, local/prod docs, fail-closed note.                               |
| #8 Real evidence connectors                 | Partial | 2     | GitHub governance sync and the first `github-security` runner are in place; broader source coverage remains. | Fixture runner tests, credential-boundary docs, normalized connector output.                           |
| #22 Authenticated repo governance connector | Partial | 2     | GitHub sync shipped in PR #62; GitLab provider and broader governance parity remain.                         | Fixture and optional live GitHub/GitLab sync evidence; token redaction tests; scope docs.              |
| #7 Controls-as-code policy engine           | Planned | 3     | Should follow enough connector evidence to evaluate real inputs.                                             | Versioned policy definitions, schema validation, deterministic outcome tests.                          |
| #13 Evidence freshness SLA workflows        | Partial | 3     | Depends on workflow records from #12 for evidence request creation.                                          | Stale evidence filters, API list/create evidence requests, test showing stale evidence changes result. |
| #14 Framework/control expansion             | Partial | 3     | Keep source-linked and readiness-gated; avoid broad compliance claims.                                       | Source refs and hashes, mapping review notes, validation coverage, evidence requirements.              |
| #9 React control-plane shell                | Partial | 4     | UI shell should use pilot APIs, not hardcoded facts.                                                         | API-backed routed pages, tenant/workspace affordance, desktop and mobile screenshots.                  |
| #18 Product-grade visualizations            | Planned | 4     | Should land after graph/workbench data contracts are stable.                                                 | AI asset graph, evidence flow, readiness trend, SLA heatmap, screenshot evidence.                      |
| #23 Repository topology workbench           | Planned | 4     | Builds on #21 and #22; links repo graph to controls and evidence.                                            | Repo graph API payload, UI details drawer, public-mode unavailable-signal state, graph tests.          |
| #12 Remediation and evidence workflow       | Planned | 5     | Needed before pilot claims owner workflow automation.                                                        | Task/evidence-request records, lifecycle tests, API/UI update path, audit trail.                       |
| #15 Snapshot room and reviewer trust center | Partial | 6     | Snapshot engine exists; reviewer experience and redaction are not done.                                      | Snapshot list/detail UI, reviewer mode, export JSON, redaction checks.                                 |
| #17 Honest shipped-vs-planned walkthrough   | Shipped | 6     | Closed by PR #63; keep it updated as roadmap issues land.                                                    | First command, artifact, app URL, shipped/partial/planned matrix, current screenshots.                 |
| #16 Headless agent workbench                | Partial | 7     | Should reuse `/api/v1` and audit boundaries from #10.                                                        | Agent route/action matrix, fixture simulator, action audit events, unsupported-claim guard.            |

## Pilot Checklist

- [x] CI quality gates and live API smoke merged through PR #20.
- [x] `/api/v1` envelope, pagination, sorting, and filter contracts closed in #11.
- [x] Public repository audit path closed in #21.
- [x] #10: auth, tenant/workspace context, RBAC, and audit boundary.
- [ ] #8: remaining source runners beyond the first `github-security` runner.
- [ ] #22: complete GitLab parity for authenticated repository governance.
- [ ] #7: policy engine and deterministic controls-as-code evaluation.
- [ ] #13: freshness SLA enforcement and stale evidence workflow.
- [ ] #14: source-linked framework/control expansion with validation.
- [ ] #9: API-backed React control-plane shell.
- [ ] #23: repository topology and governance graph workbench.
- [ ] #18: product-grade topology, trend, and workflow visualizations.
- [ ] #12: remediation tasks, evidence requests, owners, SLAs, and exceptions.
- [ ] #15: snapshot room and reviewer trust center.
- [x] #17: shipped-vs-planned public walkthrough.
- [ ] #16: headless agent workbench and guarded skill execution model.

## Update Rules

When updating this tracker:

1. Move an issue to **Partial** only when code, tests, or docs prove a usable
   slice exists.
2. Move an issue to **Shipped** only when the issue is closed or the closing PR
   includes the acceptance evidence listed above.
3. Keep deferred work explicit instead of folding it into pilot promises.
4. Add the exact verification command or artifact path to the issue or PR body.
