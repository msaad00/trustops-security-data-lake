# Framework expansion plan

TrustOps ships **source-linked** framework packs: local control IDs, short internal titles, evidence requirements, and official citations — never paywalled standard text.

## Implementation status model

| Status                        | Meaning                                              | Controls in catalog | Console posture       |
| ----------------------------- | ---------------------------------------------------- | ------------------- | --------------------- |
| `implemented_full_pack`       | Seeded controls + reviewed mappings + evidence hints | Yes                 | Included in readiness |
| `implemented_limited_mapping` | Honest seed subset with public-source citations      | Yes (subset)        | Included              |
| `referenced_only`             | Official source linked; analyst/MCP skill only       | No                  | Listed, not scored    |
| `planned`                     | Roadmap entry with zero seeded controls              | No                  | Listed as planned     |

Validation lives in `validate_catalog()` (`src/security_lakehouse/catalog.py`) and `tests/test_framework_implementation_status.py`.

## Shipped today (13 implemented)

See [FRAMEWORK_COVERAGE.md](./FRAMEWORK_COVERAGE.md) for the live matrix. Current implemented frameworks:

- SOC 2, NIST AI RMF, ISO 27001, ISO 27017, ISO 42001, NIST CSF 2.0
- FedRAMP Moderate, CMMC 2 Level 2, CIS AWS Foundations
- GDPR, HIPAA Security Rule, EU AI Act, PCI DSS v4 (limited mapping)

## Planned next (registry only)

| Framework ID     | Official source                                                                                        | Target stream       | Notes                                                          |
| ---------------- | ------------------------------------------------------------------------------------------------------ | ------------------- | -------------------------------------------------------------- |
| `iso-27701-2019` | [ISO/IEC 27701:2019](https://www.iso.org/standard/71670.html)                                          | Privacy pack        | Extends ISO 27001 PIMS; requires license review before seeding |
| `soc1`           | [AICPA SOC 1](https://www.aicpa-cima.com/topic/audit-assurance/audit-and-assurance-greater-than-soc-2) | Financial reporting | ICFR-focused; distinct evidence types from SOC 2               |

## Expansion rules (do not skip)

1. **No invented controls** — every seeded control must map to an official article/requirement ID.
2. **Evidence requirements** — each new control ships `required_evidence_types` and connector hints.
3. **Tests** — add catalog integrity, mapping coverage, and at least one pipeline fixture event per new evidence type.
4. **Copyright guardrails** — reproduce identifiers and short titles only; link official sources.
5. **Planned stays honest** — `planned` frameworks must have `seeded_control_count = 0` until a pack PR lands.

## Adding a new pack (contributor checklist)

1. Add registry row with `implementation_status` and `official_source_url`.
2. Add pack JSON under `frameworks/packs/data/` (or extend existing pack).
3. Run `uv run security-lakehouse frameworks validate` and refresh `docs/FRAMEWORK_COVERAGE.md`.
4. Add `tests/test_framework_packs.py` coverage for the new pack slug.
5. Update `docs/FRAMEWORK_PACKS.md` with evidence connector hints.

## Analyst-only / MCP skills

Frameworks marked `referenced_only` or `planned` remain visible in `/console/frameworks/` but do not affect posture until a pack ships. Agents should use `get_framework_coverage` and cite official URLs rather than inventing control text.
