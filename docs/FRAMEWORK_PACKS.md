# Framework Packs

TrustOps ships **framework packs** — complete criterion/subcategory catalogs with
reviewed mappings, evidence requirements, and evaluation rules. Packs are the
fastest path to managed GRC-style **100% framework ID coverage** while other
frameworks stay seed-and-expand.

## Full packs (100% ID coverage)

| Pack                  | Framework ID  | Controls                                             | Official source                                                                                                                     |
| --------------------- | ------------- | ---------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| SOC 2 Common Criteria | `soc2`        | **33** (CC1.1–CC9.2)                                 | [AICPA TSC 2017/2022](https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022) |
| NIST AI RMF 1.0       | `nist-ai-rmf` | **72** (all GOVERN/MAP/MEASURE/MANAGE subcategories) | [NIST AI RMF 1.0](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10)                    |

**Important:** 100% here means **every official criterion ID is seeded, mapped,
and evaluable in TrustOps**. It does not mean certification, audit opinion, or
that every point-of-focus has bespoke automated evidence yet.

## Sync packs into the catalog

```bash
security-lakehouse frameworks sync-packs
# or one pack:
security-lakehouse frameworks sync-packs --pack soc2
security-lakehouse frameworks sync-packs --pack nist-ai-rmf
```

This merges pack rows into:

- `controls/catalog.json`
- `mappings/control_articles.json`
- `mappings/control_map.json`
- `controls/bundle.lock.json` (via bundle recompute)

Hand-authored controls (e.g. richer `SOC2-CC6.1` evidence text) are **preserved**
when the `control_id` already exists.

## Verify coverage

```bash
security-lakehouse frameworks coverage --format markdown > docs/FRAMEWORK_COVERAGE.md
security-lakehouse catalog verify
```

SOC 2 and NIST AI RMF should show **100% seeded mapping coverage** with
`seeded_control_count` equal to the pack sizes above.

## Other frameworks (add as you go)

HIPAA, GDPR, EU AI Act, ISO, PCI, CIS AWS, and others remain **seed packs** —
expand incrementally using the same control schema. See
[Framework Coverage](FRAMEWORK_COVERAGE.md) for current counts.

## Custom frameworks

Add customer-specific or internal frameworks under `frameworks/custom/`:

1. Copy `frameworks/custom/example.registry.json` and `example.controls.json`.
2. Register the framework in your deployment's data directory or merge into
   `frameworks/registry.json`.
3. Add controls with full provenance fields (see `controls/catalog.json`).
4. Run `security-lakehouse controls provenance` and `security-lakehouse catalog verify`.

Custom packs can reuse evaluation rule aliases from `policy.py` and map to
your connectors' evidence types.

## Evaluation rules by domain

Pack-generated controls use deterministic rule aliases:

| Risk domain                                        | Default rule                                 |
| -------------------------------------------------- | -------------------------------------------- |
| identity, monitoring, controls-operations, ai-risk | `fail_when_open_violation_or_stale_evidence` |
| vendor-risk                                        | `fail_when_high_severity_open`               |
| governance, risk-management, ai-governance         | `fail_when_missing_evidence`                 |

Tune per control after sync by editing `evaluation_rule` in the catalog.

## Roadmap

- SOC 2 **Availability / Confidentiality / Processing Integrity / Privacy** TSC
  extensions (beyond common criteria)
- NIST **CSF 2.0** full pack
- Pack-specific evidence requirement templates linked to connector catalogs

See [ROADMAP.md](../ROADMAP.md).
