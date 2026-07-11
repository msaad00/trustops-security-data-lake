# Delivery tracker (#449)

Consolidated view of open work. Goal: **≤4 PRs in flight** at a time instead of one-issue-one-PR.

Last updated: **2026-07-11** (post #462 merge — queue empty, #427 in flight)

## PR queue (max 4)

| PR branch                          | Issues | Status                                    |
| ---------------------------------- | ------ | ----------------------------------------- |
| `cursor/playwright-e2e-smoke-d259` | #427   | 🟡 In progress — Playwright console smoke |

## Stream map

| Stream                        | Merged PR        | Issues bundled                                                                                                       | Status       |
| ----------------------------- | ---------------- | -------------------------------------------------------------------------------------------------------------------- | ------------ |
| **A — Connectors**            | #447, #448       | SIEM + runtime runners                                                                                               | ✅ Done      |
| **B — Platform hygiene**      | #450             | #423 LICENSE, #424 Python 3.12, #426 types dedup, #416 ESLint CI                                                     | ✅ Done      |
| **C — Console UX + live**     | #451, #459       | #428 AI governance route, #422 SSE ai-governance, #429 agent drawer, #430 signup, #431 a11y, #432 command palette    | ✅ Done      |
| **D — Repo graph**            | #452             | #23 graph workbench (+ #22 connector scope mostly via `github-security` / `gitlab-security`)                         | ✅ Done      |
| **E — Framework + freshness** | #454, #460, #461 | #14 framework expansion + equivalence mapping + limited packs (GDPR/HIPAA/PCI/EU AI Act), #13 evidence freshness SLA | ✅ Done      |
| **F — Backend platform**      | #458, #462       | #419 MCP remote-read, #434 session hashing, #421 lake_eval tests; **deferred:** #415, #413, #420 rate limit          | 🟡 Partial   |
| **G — Docs + playbooks**      | #453             | #418 CONSOLE_UX.md, #433 HRIS playbook                                                                               | ✅ Done      |
| **H — Jobs API**              | #455             | #435 unified mid-run jobs dashboard                                                                                  | ✅ Done      |
| **I — Console E2E**           | —                | #427 Playwright smoke (dashboard + audit-room)                                                                       | 🟡 In flight |

## Merged this session

| PR                                                                      | Closes               |
| ----------------------------------------------------------------------- | -------------------- |
| [#462](https://github.com/msaad00/trustops-security-data-lake/pull/462) | #421 lake_eval tests |
| [#461](https://github.com/msaad00/trustops-security-data-lake/pull/461) | #14 limited packs    |
| [#460](https://github.com/msaad00/trustops-security-data-lake/pull/460) | #14 equivalence      |

## Deferred (keep open)

| Issue              | Notes                                                      |
| ------------------ | ---------------------------------------------------------- |
| #436               | CycloneDX/SPDX AIBOM ingest/export (P3)                    |
| #415, #413         | Large backend split / API migration — next wave            |
| #425               | Split hooks.ts by domain (frontend refactor, non-blocking) |
| #420               | Distributed rate limiting for multi-replica                |
| #96, #15, #18, #16 | Experience epics — coordinate with product lane            |

## Epics (rollup only)

- **#411** Repository audit roadmap — P1/P2 items #413–#435 roll up here
- **#96** Experience uplift — overlaps #15, #18, #428

## Duplicates / close manually

GitHub issues still open but work is on `main` — close when convenient:

- #423, #424, #426, #416 (#450)
- #428, #422, #429 (#451)
- #418, #433 (#453)
- #13, #14, #421 (#454, #460, #461, #462)
- #417 → duplicate of #22 + #23

## Next wave (pick ≤4)

1. **#415** — server_app route split (scoped slice)
2. **#420** — distributed rate limiting
3. **#436** — CycloneDX/SPDX AIBOM (P3)
4. **#425** — split hooks.ts by domain

## CI watchlist

Before merge: `make ci`, `make web-ci`, `make smoke`, `bash tools/run_e2e_console.sh`, `pre-commit run --all-files`.
