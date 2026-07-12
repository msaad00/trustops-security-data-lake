# Delivery tracker

**Single source of truth:** GitHub issue **#474** (Wave 2). Wave 1 tracker **#449** is retired — do not open new work against #449 streams.

Last updated: **2026-07-12**

## Active wave — agent-first (#474)

| Stream                      | Branch                             | Issue | Status                     |
| --------------------------- | ---------------------------------- | ----- | -------------------------- |
| **I — Headless connectors** | `cursor/headless-connectors-d259`  | #475  | 🟡 PR ready                |
| **J — Agent contracts**     | `cursor/agent-contracts-d259`      | #476  | 🟡 PR ready (stacks I)     |
| **K — CI posture gates**    | `cursor/ci-posture-gates-d259`     | #477  | 🔲 Next                    |
| **L — Agent harness UI**    | `cursor/agent-harness-d259`        | #478  | 🔲 Absorbs #16; #429 done  |
| **M — Human connect UX**    | `cursor/human-connect-ux-d259`     | #479  | 🔲 managed GRC SaaS wizard |
| **N — Console copy**        | `cursor/console-human-polish-d259` | #480  | 🔲 Partial in #475         |

**Positioning:** headless/agents/CI first; human console second. Default connect path is **agentless read-only API** — no customer SDL required ([CONNECTORS.md](CONNECTORS.md), [HEADLESS_CONNECTOR_SETUP.md](playbooks/HEADLESS_CONNECTOR_SETUP.md)).

## Wave 1 — complete (#449 streams A–H)

All Wave 1 streams merged (#447–#473). See [ISSUE_CONSOLIDATION.md](ISSUE_CONSOLIDATION.md) for issue→PR mapping.

## Open issues — keep vs close

| Keep open     | Role                                                       |
| ------------- | ---------------------------------------------------------- |
| **#474**      | Wave 2 epic tracker (only tracker to use)                  |
| **#475–#480** | Wave 2 child issues                                        |
| **#96**       | Human UX epic rollup only (#479, #480, #18) — not headless |
| **#16**       | Closes when #478 merges (harness workbench AC)             |
| **#14**       | Framework expansion (ongoing packs)                        |
| **#18**       | Topology/workflow viz gaps                                 |
| **#22**       | Org-level repo governance beyond per-repo connectors       |
| **#15**       | Narrow: exec viz / trust-center polish not in audit room   |
| **#411**      | Backend audit roadmap rollup                               |
| **#434**      | Session hashing — verify #458; close if satisfied          |
| **#436**      | Deferred P3 AIBOM                                          |

| Close (duplicate / shipped) | Shipped by                           |
| --------------------------- | ------------------------------------ |
| #449                        | Superseded by #474                   |
| #417                        | Duplicate of #22 + #23               |
| #416, #423, #424            | #450                                 |
| #418, #433                  | #453                                 |
| #422, #428, #429            | #451                                 |
| #430, #431, #432            | #456                                 |
| #93                         | Shipped; #476 extends OpenAPI/skills |

## CI before merge

`make ci`, `make web-ci`, `tools/run_e2e_console.sh`, `pre-commit run --all-files`.
