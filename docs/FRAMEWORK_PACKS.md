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

Pack source data for every full and limited pack, plus connector hints, lives
under `frameworks/packs/data/` (see that directory's `README.md` for the file
list). Connector hints power framework drill-down recommendations
(`evidence_hints.py`).

## Manifest schema

Every framework pack is **manifest-driven**: a framework's control
identifiers, titles, and source citation are data in a JSON file under
`frameworks/packs/data/`, not a bespoke Python function. Each pack's
`*_specs()` function (in `framework_packs.py` or `limited_packs.py`) is a
thin wrapper: it calls
`pack_from_manifest(manifest_path, transform=...)` — see
`src/security_lakehouse/pack_manifest.py` — passing a small, named,
per-framework **transform** function that handles whatever logic doesn't
belong in data (ID normalization, risk-domain/owner lookups, evidence
wording).

A manifest is a JSON object with:

- `schema` (optional) — `"trustops.framework_pack_manifest.v1"`.
- `source` — the pinned citation: at minimum a `url`; the `nist_csf_2_core.json`
  precedent also pins a `sha256` digest and a `locator` for source-integrity
  testing (see `tests/test_csf_source_integrity.py`).
- a rows key (`"rows"` by default; `pack_from_manifest(..., rows_key=...)`
  can point at another key, e.g. pre-existing files' `"requirements"` or
  `"controls"`) holding either:
  - an array of objects, `[{"id": "1.1", "title": "..."}, ...]` — the
    default new-manifest shape, and the shape already used by
    `cis_aws_v3.json`, `cmmc_2_level2.json`, and `iso_27017_2015.json`.
    Extra per-row fields (e.g. a limited pack's `risk_domain`/`owner`/
    `asset_types`) pass through to the transform via `row.extra`.
  - an object mapping identifier -> title, `{"GV.OC-01": "...", ...}` — the
    `nist_csf_2_core.json` precedent's `"outcomes"` shape.
  - an array of plain identifier strings, `["AC-1", "AC-2", ...]` — for
    frameworks with no distinct per-ID title text (e.g.
    `nist_800_53_rev5_moderate.json`'s `"control_ids"`).

### Add a new framework

1. Add `frameworks/packs/data/<framework>.json` with the framework's official
   identifiers (and titles, where distinct per-ID text exists — never
   transcribe licensed normative text, short internal titles only).
2. Write a small transform function, e.g. `_<framework>_row_transform(row:
PackManifestRow) -> PackControlSpec`, covering whatever isn't flat data:
   ID normalization, a risk-domain/owner lookup, `evidence_requirement`
   wording. Reuse `_soc2_owner`/`_soc2_assets`/`_soc2_evaluation_rule` where
   the framework's evaluation shape matches the existing ones.
3. Add `<framework>_specs() -> list[PackControlSpec]` that calls
   `pack_from_manifest(PACK_DATA_DIR / "<framework>.json", transform=...)`,
   and register it in `PACK_BUILDERS` (or `LIMITED_PACK_BUILDERS` for a
   partial-coverage pack).
4. Write a row-level identity test if converting an existing framework, or a
   coverage test (count + identifier set) for a new one — see
   `tests/test_framework_packs.py` and `tests/test_pack_manifest.py`.
5. Run `security-lakehouse frameworks sync-packs --pack <framework>` then
   `security-lakehouse catalog verify` (regenerate the lockfile per the
   command above if it reports stale).

## Verify coverage

```bash
security-lakehouse frameworks coverage --format markdown > docs/FRAMEWORK_COVERAGE.md
security-lakehouse catalog verify
```

Full packs should show **100% seeded mapping coverage** with `seeded_control_count`
equal to the pack sizes above.

## Limited-mapping packs (GDPR, HIPAA, PCI, EU AI Act)

Run `frameworks sync-packs --pack gdpr --pack hipaa --pack pci-dss --pack eu-ai-act`
to merge expanded honest subsets (20 GDPR articles, 18 HIPAA sections, 12 PCI
requirements, 15 EU AI Act articles as of v0.2.x). These are **not** full
official catalogs — see [Framework Coverage](FRAMEWORK_COVERAGE.md) for counts.

PCI DSS cites **v4.0.1** and seeds all 12 principal requirements at the
requirement level (`Req-1` … `Req-12`). It stays `implemented_limited_mapping`:
the x.y / x.y.z sub-requirements are not seeded, because the PCI SSC standard
is distributed under a license click-through and there is no official
machine-readable identifier source to pin them to. The v4.0-citing control
versions (1.0.0) remain in `controls/history.jsonl`, so as-of views of audits
before 2026-09-23 still show the v4.0 citation.

## Other frameworks (add as you go)

ISO 27701 and SOC 1 remain **planned** in the registry. Expand additional
frameworks incrementally using the same control schema. SOC 1 has no official
control catalog to seed from (see
[Framework expansion plan](FRAMEWORK_EXPANSION_PLAN.md#soc-1-why-it-stays-planned)).

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
