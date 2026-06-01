---
name: soc2-control-analyst
description: >-
  Assess SOC 2-oriented control posture from local TrustOps evidence. Use when
  an agent needs to review SOC 2 control mappings, current posture, violations,
  evidence freshness, audit snapshots, or owner remediation queues. Guardrail:
  use official AICPA Trust Services Criteria references and do not invent
  criteria or claim audit readiness.
---

# SOC 2 Control Analyst

Use this skill for SOC 2-oriented assessment from local evidence.

## Official Source Guardrail

Load `references/sources.md` before making framework claims. The skill may
reference official source names and URLs, but must not reproduce paywalled or
licensed standard text.

## Workflow

1. Read `GET /api/v1/posture/current` or `build/lakehouse/gold/current_posture.json`.
2. Filter controls where `framework == "SOC 2"`.
3. Pull violations for those controls from `GET /api/v1/violations`.
4. Validate each claim against local evidence fields:
   - `control_id`
   - `event_id`
   - `asset_id`
   - `asset_owner`
   - `evidence_ref`
   - `raw_sha256`
5. Mark unmapped criteria as `not_mapped`.
6. Recommend owner actions without claiming certification status.

## Response Rules

- Say "SOC 2-oriented" unless a formal audit scope is supplied.
- Do not invent AICPA criteria, points of focus, or auditor expectations.
- Cite local evidence and official source references.
- Use snapshots for point-in-time requests.
