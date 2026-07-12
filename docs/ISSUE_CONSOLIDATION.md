# Issue consolidation map

Avoid duplicate PRs. Before opening work, check this table.

## Wave 2 (active — #474)

| Issue                              | Do not duplicate with           | Notes                                                               |
| ---------------------------------- | ------------------------------- | ------------------------------------------------------------------- |
| #475 Headless connector lifecycle  | —                               | ✅ #482 merged; close issue on GitHub                               |
| #476 Agent skill catalog + OpenAPI | ~~#93~~ (closed)                | ✅ #481 merged; close issue on GitHub                               |
| #477 CI posture gates              | —                               | GitHub Action / script                                              |
| #478 Agent harness workbench       | #16 (parent), ~~#429~~ (closed) | Drawer shipped #451; #478 = skills + fixture mode + approval polish |
| #479 Human connect onboarding      | #473 console drawer             | Wizard/onboarding UX                                                |
| #480 Console agent-first copy      | #472, #473 density              | Terminology partially in #475; empty states + notifications remain  |

## Shipped — close if still open

| Issue     | PR      | Deliverable                                        |
| --------- | ------- | -------------------------------------------------- |
| **#475**  | #482    | Headless connector playbook + lifecycle test       |
| **#476**  | #481    | AGENT_SKILLS + OpenAPI + resource catalog          |
| #449      | —       | Retired tracker → use **#474**                     |
| #417      | —       | Duplicate of #22 + #23                             |
| #416      | #450    | ESLint CI                                          |
| #423      | #450    | LICENSE                                            |
| #424      | #450    | Python 3.12 CI                                     |
| #418      | #453    | CONSOLE_UX.md                                      |
| #433      | #453    | HRIS playbook                                      |
| #422      | #451    | SSE ai-governance                                  |
| #428      | #451    | /ai-governance route                               |
| #429      | #451    | AgentRunDrawer                                     |
| #430      | #456    | Signup flows (OSS trimmed #470)                    |
| #431      | #456    | A11y pass                                          |
| #432      | #456    | Command palette / breadcrumbs                      |
| #93       | (prior) | MCP catalog; #476 adds committed OpenAPI + skills  |
| #13       | #454    | Evidence freshness SLA                             |
| #23       | #452    | Repo graph workbench                               |
| #419      | #458    | MCP remote read                                    |
| #434      | #458    | Session PBKDF2 — re-verify before new work         |
| #421      | #462    | lake_eval tests                                    |
| #435      | #455    | Platform jobs API                                  |
| #427      | #463    | Playwright smoke                                   |
| #470–#473 | merged  | OSS cleanup, connectors UX, density, E2E workflow  |
| #481–#482 | merged  | Agent contracts + headless connectors (Wave 2 I–J) |

Close batch script: [ISSUE_CLOSEOUT.md](ISSUE_CLOSEOUT.md) · `./tools/close_shipped_issues.sh`

## Epics — scope only (no new child issues)

| Epic     | Owns                                   | Does not own                                 |
| -------- | -------------------------------------- | -------------------------------------------- |
| **#474** | Wave 2 streams I–N                     | —                                            |
| **#96**  | Human console polish (#479, #480, #18) | Headless (#475–#477), agent contracts (#476) |
| **#16**  | Harness AC                             | Close when #478 merges                       |
| **#411** | Backend audit items                    | Console UX                                   |
| **#22**  | Org-level GitHub/GitLab governance     | Per-repo `github-security` (shipped)         |

## Default product path (no issue duplication)

```text
Agentless read-only API connectors (default)
  → probe → enable → sync → eval
Optional: existing Snowflake/ClickHouse lake read
Human console: peer surface on same /api/v1
```

See [HEADLESS_CONNECTOR_SETUP.md](playbooks/HEADLESS_CONNECTOR_SETUP.md).
