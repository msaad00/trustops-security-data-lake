# Issue closeout runbook

Drain duplicate and shipped issues so **#474** is the only active tracker. Run after each Wave 2 merge batch.

## Batch 2 — after #482 + #481 (2026-07-12)

| Close            | Shipped by             | Still open? |
| ---------------- | ---------------------- | ----------- |
| **#475**         | #482                   | yes         |
| **#476**         | #481                   | yes         |
| #449             | Wave 1 complete → #474 | yes         |
| #417             | duplicate #22 + #23    | yes         |
| #416, #423, #424 | #450                   | yes         |
| #433             | #453                   | yes         |
| #422, #428, #429 | #451                   | yes         |
| #431, #432       | #456                   | yes         |

Already closed on GitHub: #418, #430, #93.

## One command (maintainer)

```bash
./tools/close_shipped_issues.sh
```

Dry run:

```bash
DRY_RUN=1 ./tools/close_shipped_issues.sh
```

Cloud agent tokens cannot close issues (403 on `addComment`). A repo owner must run the script locally or close manually with the comments in `tools/close_shipped_issues.sh`.

## After closeout

- **Keep open:** #474 (epic), #477–#480 (Wave 2 streams), #96, #16, #411, #22, #14, #18, #15, #434, #436
- **Next PR stream:** #477 CI posture gates (`cursor/ci-posture-gates-d259`)

See [DELIVERY_TRACKER.md](DELIVERY_TRACKER.md) and [ISSUE_CONSOLIDATION.md](ISSUE_CONSOLIDATION.md).
