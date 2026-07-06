# Framework Packs

TrustOps ships **framework packs** — complete criterion/subcategory catalogs with
reviewed mappings, evidence requirements, and evaluation rules. Packs are the
fastest path to managed GRC-style **100% framework ID coverage** while other
frameworks stay seed-and-expand.

## Full packs (100% ID coverage)

| Pack                        | Framework ID          | Controls                                                | Official source                                                                                                                                    |
| --------------------------- | --------------------- | ------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| SOC 2 Common Criteria       | `soc2`                | **33** (CC1.1–CC9.2)                                    | [AICPA TSC 2017/2022](https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022)                |
| SOC 2 TSC extensions        | `soc2`                | **28** supplemental (A1, C1, PI1, P1–P8) — **61 total** | same                                                                                                                                               |
| NIST AI RMF 1.0             | `nist-ai-rmf`         | **72** (all GOVERN/MAP/MEASURE/MANAGE subcategories)    | [NIST AI RMF 1.0](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10)                                   |
| NIST CSF 2.0 Core           | `nist-csf-2.0`        | **106** subcategories (GOVERN through RECOVER)          | [NIST Cybersecurity Framework 2.0](https://www.nist.gov/cyberframework)                                                                            |
| FedRAMP Moderate foundation | `fedramp-moderate`    | **287** (NIST SP 800-53 Rev 5 Moderate baseline)        | [NIST SP 800-53B](https://csrc.nist.gov/publications/detail/sp/800-53b/final)                                                                      |
| CIS AWS Foundations v3.0    | `cis-aws` / `cis_aws` | **62** recommendations                                  | [CIS AWS Benchmark](https://www.cisecurity.org/benchmark/amazon_web_services)                                                                      |
| CMMC 2.0 Level 2            | `cmmc-2-level2`       | **110** practices (NIST SP 800-171 Rev 2)               | [NIST SP 800-171 Rev 2](https://csrc.nist.gov/publications/detail/sp/800-171/rev-2/final) / [CMMC](https://dodcio.defense.gov/CMMC/Documentation/) |
| ISO/IEC 27001:2022 Annex A  | `iso-27001-2022`      | **93** controls                                         | [ISO/IEC 27001:2022](https://www.iso.org/standard/27001)                                                                                           |
| ISO/IEC 27017:2015 Cloud    | `iso-27017-2015`      | **47** clauses (40 ISO 27002 + 7 CLD)                   | [ISO/IEC 27017:2015](https://www.iso.org/standard/43757.html)                                                                                      |
| ISO/IEC 42001:2023 Annex A  | `iso-42001-2023`      | **38** AI controls                                      | [ISO/IEC 42001:2023](https://www.iso.org/standard/42001)                                                                                           |

**Important:** 100% here means **every official criterion ID is seeded, mapped,
and evaluable in TrustOps**. It does not mean certification, audit opinion, or
that every point-of-focus has bespoke automated evidence yet.

**FedRAMP note:** FedRAMP Rev 5 Moderate authorization selects **323** controls
from NIST SP 800-53 Rev 5 with FedRAMP overlays. This pack seeds the **NIST
Moderate baseline (287 controls)** — the authoritative OSCAL control set that
forms the FedRAMP Moderate foundation. FedRAMP-specific parameter overlays ship
in a follow-up.

## Sync packs into the catalog

```bash
security-lakehouse frameworks sync-packs
# or one pack:
security-lakehouse frameworks sync-packs --pack nist-csf-2.0
security-lakehouse frameworks sync-packs --pack fedramp-moderate
security-lakehouse frameworks sync-packs --pack cis-aws
security-lakehouse frameworks sync-packs --pack cmmc-2-level2
security-lakehouse frameworks sync-packs --pack iso-27001-2022
security-lakehouse frameworks sync-packs --pack iso-27017-2015
security-lakehouse frameworks sync-packs --pack iso-42001-2023
make framework-packs
```

This merges pack rows into:

- `controls/catalog.json`
- `mappings/control_articles.json`
- `mappings/control_map.json`
- `controls/bundle.lock.json` (via bundle recompute)
- `frameworks/verified_article_ids.json` (regenerate from mappings after sync)

Hand-authored controls (e.g. richer `SOC2-CC6.1` evidence text) are **preserved**
when the `control_id` already exists.

Pack source data for FedRAMP and CIS lives under `frameworks/packs/data/`.

## Verify coverage

```bash
security-lakehouse frameworks coverage --format markdown > docs/FRAMEWORK_COVERAGE.md
security-lakehouse catalog verify
```

Full packs should show **100% seeded mapping coverage** with `seeded_control_count`
equal to the pack sizes above.

## Other frameworks (add as you go)

HIPAA, GDPR, EU AI Act, PCI, and others remain **seed packs** — expand
incrementally using the same control schema. See
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

- FedRAMP **Rev 5 overlay** controls beyond NIST Moderate (323-selected set)
- SOC 2 **Availability / Confidentiality / Processing Integrity / Privacy** TSC
- Pack-specific evidence requirement templates linked to connector catalogs

See [ROADMAP.md](../ROADMAP.md).
