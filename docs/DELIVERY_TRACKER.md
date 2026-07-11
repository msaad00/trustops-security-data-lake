# Delivery tracker (#449)

Consolidated view of open work. Goal: **≤4 PRs in flight** at a time instead of one-issue-one-PR.

Last updated: **2026-07-11** (next wave: #415 + #420 in flight)

## PR queue (max 4)

| PR branch                           | Issues | Status                                      |
| ----------------------------------- | ------ | ------------------------------------------- |
| `cursor/server-app-gov-router-d259` | #415   | 🟡 In progress — gov-compliance APIRouter   |
| `cursor/rate-limit-redis-d259`      | #420   | 🟡 In progress — Redis-backed rate limiting |

## Stream map

| Stream                        | Merged PR        | Issues bundled                                                                                                 | Status     |
| ----------------------------- | ---------------- | -------------------------------------------------------------------------------------------------------------- | ---------- |
| **A — Connectors**            | #447, #448       | SIEM + runtime runners                                                                                         | ✅ Done    |
| **B — Platform hygiene**      | #450             | #423 LICENSE, #424 Python 3.12, #426 types dedup, #416 ESLint CI                                               | ✅ Done    |
| **C — Console UX + live**     | #451, #459, #463 | #428 AI governance, #422 SSE, #429 drawer, #430–#432 console polish, #427 Playwright E2E                       | ✅ Done    |
| **D — Repo graph**            | #452             | #23 graph workbench                                                                                            | ✅ Done    |
| **E — Framework + freshness** | #454, #460, #461 | #14 framework + equivalence + limited packs, #13 evidence freshness SLA                                        | ✅ Done    |
| **F — Backend platform**      | #458, #462       | #419 MCP, #434 sessions, #421 lake_eval; **in flight:** #415 server split, #420 rate limit; **deferred:** #413 | 🟡 Partial |
| **G — Docs + playbooks**      | #453             | #418 CONSOLE_UX.md, #433 HRIS playbook                                                                         | ✅ Done    |
| **H — Jobs API**              | #455             | #435 unified mid-run jobs dashboard                                                                            | ✅ Done    |

## Merged this session

| PR                                                                      | Closes               |
| ----------------------------------------------------------------------- | -------------------- |
| [#463](https://github.com/msaad00/trustops-security-data-lake/pull/463) | #427 Playwright E2E  |
| [#462](https://github.com/msaad00/trustops-security-data-lake/pull/462) | #421 lake_eval tests |
| [#461](https://github.com/msaad00/trustops-security-data-lake/pull/461) | #14 limited packs    |
| [#460](https://github.com/msaad00/trustops-security-data-lake/pull/460) | #14 equivalence      |

## Deferred (keep open)

| Issue              | Notes                                                      |
| ------------------ | ---------------------------------------------------------- |
| #436               | CycloneDX/SPDX AIBOM ingest/export (P3)                    |
| #413               | Console → /api/v1 migration plan                           |
| #425               | Split hooks.ts by domain (frontend refactor, non-blocking) |
| #96, #15, #18, #16 | Experience epics — coordinate with product lane            |

## Next wave (after #415/#420)

1. **#436** — CycloneDX/SPDX AIBOM (P3)
2. **#425** — split hooks.ts by domain
3. **#415 wave 2** — platform/remediation routers
4. **#413** — API v1 migration plan doc

## CI watchlist

Before merge: `make ci`, `make web-ci`, `make smoke`, `bash tools/run_e2e_console.sh`, `pre-commit run --all-files`.
