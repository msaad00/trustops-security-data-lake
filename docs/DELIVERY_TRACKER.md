# Delivery tracker (#449)

Consolidated view of open work. Goal: **≤4 PRs in flight** at a time instead of one-issue-one-PR.

Last updated: **2026-07-10** (post #450–#454 merge)

## PR queue (max 4)

| PR branch | Issues | Status |
|-----------|--------|--------|
| `cursor/unified-jobs-d259` | #435 | 🔵 In review |
| `cursor/backend-platform-d259` | #419, #434 | 🔵 In review |
| `cursor/console-polish-d259` | #430, #431, #432 | 🔵 In review |
| `cursor/delivery-tracker-d259` | #449 (this doc) | 🔵 In review |

## Stream map

| Stream | Merged PR | Issues bundled | Status |
|--------|-----------|----------------|--------|
| **A — Connectors** | #447, #448 | SIEM + runtime runners | ✅ Done |
| **B — Platform hygiene** | #450 | #423 LICENSE, #424 Python 3.12, #426 types dedup, #416 ESLint CI | ✅ Done |
| **C — Console UX + live** | #451 + `console-polish` | #428 AI governance route, #422 SSE ai-governance, #429 agent drawer, #430 signup, #431 a11y, #432 command palette | 🟡 #451 merged; signup/a11y/nav in PR queue |
| **D — Repo graph** | #452 | #23 graph workbench (+ #22 connector scope mostly via `github-security` / `gitlab-security`) | ✅ Done |
| **E — Framework + freshness** | #454 | #14 framework expansion, #13 evidence freshness SLA | ✅ Done |
| **F — Backend platform** | `backend-platform` | #419 MCP remote-read, #434 session hashing; **deferred:** #415 split server_app, #413 api/v1 plan, #421 lake_eval (tests exist), #420 rate limit | 🟡 Partial — remote-read + sessions in PR queue |
| **G — Docs + playbooks** | #453 | #418 CONSOLE_UX.md, #433 HRIS playbook | ✅ Done |
| **H — Jobs API** | `unified-jobs` | #435 unified mid-run jobs dashboard | 🔵 In review |

## Deferred (keep open)

| Issue | Notes |
|-------|-------|
| #436 | CycloneDX/SPDX AIBOM ingest/export (P3) |
| #427 | Playwright E2E smoke (dashboard + audit-room) |
| #415, #413 | Large backend split / API migration — next wave after queue drains |
| #425 | Split hooks.ts by domain (frontend refactor, non-blocking) |
| #420 | Distributed rate limiting for multi-replica |
| #96, #15, #18, #16 | Experience epics — coordinate with product lane |

## Epics (rollup only)

- **#411** Repository audit roadmap — P1/P2 items #413–#435 roll up here
- **#96** Experience uplift — overlaps #15, #18, #428

## Duplicates

- **#417** → duplicate of #22 + #23 (repo graph connector + workbench; see #452)

## CI watchlist

Before merge: `make ci`, `make web-ci`, `make smoke`, `pre-commit run --all-files`.

## Next after queue

1. Merge the four PRs above
2. Close #435, #419, #434, #430–#432, #449 when landed
3. Pick **one** of: #427 Playwright E2E, #421 lake_eval eval_overdue test, or #415 route split (scoped slice)
