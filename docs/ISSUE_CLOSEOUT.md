# Issue closeout runbook

Drain duplicate and shipped issues so **#474** is the only active tracker. Run after each Wave 2 merge batch.

## Batch 2 — after #482 + #481 (2026-07-12)

| Close            | Shipped by             |
| ---------------- | ---------------------- |
| **#475**         | #482                   |
| **#476**         | #481                   |
| #449             | Wave 1 complete → #474 |
| #417             | duplicate #22 + #23    |
| #416, #423, #424 | #450                   |
| #433             | #453                   |
| #422, #428, #429 | #451                   |
| #431, #432       | #456                   |

Already closed on GitHub: #418, #430, #93.

## Batch 3 — after #484 + #485 + #486 + #487 (2026-07-13)

| Close    | Shipped by   | PR                |
| -------- | ------------ | ----------------- |
| **#477** | CI gate      | #484              |
| **#478** | Harness UI   | #485 (closes #16) |
| **#479** | Onboarding   | #486              |
| **#480** | Console copy | #487              |

Run **after** all four PRs merge:

```bash
./tools/close_shipped_issues.sh
```

Or close batch 3 only (comment out batch 1–2 in script if already done).

## One command (maintainer)

```bash
DRY_RUN=1 ./tools/close_shipped_issues.sh   # preview
./tools/close_shipped_issues.sh
```

Cloud agent tokens cannot close issues (403 on `addComment`). A repo owner must run the script locally.

## After closeout

- **Keep open:** #474 (epic), #96, #411, #22, #14, #18, #15, #434, #436
- **#16** closes with #478 / #485

See [DELIVERY_TRACKER.md](DELIVERY_TRACKER.md) and [ISSUE_CONSOLIDATION.md](ISSUE_CONSOLIDATION.md).
