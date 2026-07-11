# Delivery tracker (#449)

Consolidated view of open work. Goal: **≤4 PRs in flight** at a time instead of one-issue-one-PR.

Last updated: **2026-07-11** (post #464 merge; #465 + closeout in flight)

## PR queue (max 4)

| PR branch                            | Issues     | Status                                 |
| ------------------------------------ | ---------- | -------------------------------------- |
| `cursor/rate-limit-redis-d259`       | #420       | 🟡 CI fix pushed — Redis rate limit    |
| `cursor/issue-closeout-tracker-d259` | #449, #413 | 🟡 In progress — tracker + API v1 plan |
| `cursor/hooks-types-hygiene-d259`    | #425, #426 | 🔜 Next — hooks split + types dedup    |

## Stream map

| Stream                        | Merged PR        | Issues bundled                                                                                                  | Status     |
| ----------------------------- | ---------------- | --------------------------------------------------------------------------------------------------------------- | ---------- |
| **A — Connectors**            | #447, #448       | SIEM + runtime runners                                                                                          | ✅ Done    |
| **B — Platform hygiene**      | #450             | #423 LICENSE, #424 Python 3.12, #426 types dedup, #416 ESLint CI                                                | ✅ Done    |
| **C — Console UX + live**     | #451, #459, #463 | #428 AI governance, #422 SSE, #429 drawer, #430–#432 console polish, #427 Playwright E2E                        | ✅ Done    |
| **D — Repo graph**            | #452             | #23 graph workbench                                                                                             | ✅ Done    |
| **E — Framework + freshness** | #454, #460, #461 | #14 framework + equivalence + limited packs, #13 evidence freshness SLA                                         | ✅ Done    |
| **F — Backend platform**      | #458, #462, #464 | #419 MCP, #434 sessions, #421 lake_eval, #415 wave 1 gov router; **in flight:** #420 rate limit; **plan:** #413 | 🟡 Partial |
| **G — Docs + playbooks**      | #453             | #418 CONSOLE_UX.md, #433 HRIS playbook                                                                          | ✅ Done    |
| **H — Jobs API**              | #455             | #435 unified mid-run jobs dashboard                                                                             | ✅ Done    |

## Merged this session

| PR                                                                      | Closes / advances       |
| ----------------------------------------------------------------------- | ----------------------- |
| [#464](https://github.com/msaad00/trustops-security-data-lake/pull/464) | #415 wave 1 gov router  |
| [#463](https://github.com/msaad00/trustops-security-data-lake/pull/463) | #427 Playwright E2E     |
| [#462](https://github.com/msaad00/trustops-security-data-lake/pull/462) | #421 lake_eval tests    |
| [#461](https://github.com/msaad00/trustops-security-data-lake/pull/461) | #14 limited packs       |
| [#460](https://github.com/msaad00/trustops-security-data-lake/pull/460) | #14 equivalence mapping |

## Close on GitHub (work on `main`)

These issues are satisfied by merged PRs — close manually to drain the backlog:

| Issue                      | Closed by                    |
| -------------------------- | ---------------------------- |
| #423 LICENSE               | #450                         |
| #424 Python 3.12           | #450                         |
| #426 types dedup (partial) | #450 / follow-up #426        |
| #416 ESLint CI             | #450                         |
| #428, #422, #429           | #451                         |
| #430, #431, #432           | #456                         |
| #418, #433                 | #453                         |
| #419, #434                 | #458                         |
| #421                       | #462                         |
| #427                       | #463                         |
| #415 (wave 1)              | #464 — keep open for wave 2+ |
| #13                        | #454                         |
| #14                        | #460, #461                   |
| #417                       | duplicate of #22 + #23       |

## Deferred (keep open)

| Issue              | Notes                                   |
| ------------------ | --------------------------------------- |
| #436               | CycloneDX/SPDX AIBOM ingest/export (P3) |
| #425               | Split hooks.ts by domain (in flight)    |
| #426               | types.ts dedup (in flight)              |
| #415 waves 2+      | platform, remediation, auth routers     |
| #96, #15, #18, #16 | Experience epics                        |

## Next wave (after #465 + hooks hygiene)

1. **#415 wave 2** — platform + remediation routers
2. **#436** — CycloneDX/SPDX AIBOM (scoped ingest)
3. **API v1 Phase 1** — console read paths per `docs/API_V1_MIGRATION.md`

## CI watchlist

Before merge: `make ci`, `make web-ci`, `make smoke`, `bash tools/run_e2e_console.sh`, `pre-commit run --all-files`.
