# Framework Coverage Matrix

TrustOps tracks framework support as source-linked controls, evidence
requirements, versioned evaluation rules, and reviewed mappings. This page is
the detailed coverage ledger. The README and product visuals should link here
instead of repeating long caveats in the hero.

## Current Coverage

This is the generated seeded-control ledger. Regenerate it with:

```bash
security-lakehouse frameworks coverage --format markdown
```

The coverage percentage below means **reviewed mappings for controls seeded in
this repo**. It does not mean full framework, audit, or certification coverage.

Frameworks: 8
Seeded controls: 34
Reviewed mappings: 34
Asset types modeled: 13
Control-to-asset applicability links: 92
Seeded mapping coverage: 100.0%

| Framework                                                  | Official source                                                                                                                                                                            | Seeded controls | Reviewed mappings | Seeded mapping coverage | Source state | Source policy                 |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------: | ----------------: | ----------------------: | ------------ | ----------------------------- |
| EU AI Act - Regulation (EU) 2024/1689                      | [EUR-Lex - Regulation (EU) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)                                                                                                      |               6 |                 6 |                  100.0% | never pulled | public-source citation        |
| GDPR - EU General Data Protection Regulation (2016/679)    | [EUR-Lex - Regulation (EU) 2016/679](https://eur-lex.europa.eu/eli/reg/2016/679/oj)                                                                                                        |               6 |                 6 |                  100.0% | never pulled | public-source citation        |
| HIPAA Security Rule (45 CFR Parts 160, 162, 164)           | [U.S. HHS HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/index.html)                                                                                            |               6 |                 6 |                  100.0% | never pulled | public-source citation        |
| ISO/IEC 27001:2022 Information security management systems | [ISO/IEC 27001:2022](https://www.iso.org/standard/27001)                                                                                                                                   |               3 |                 3 |                  100.0% | never pulled | source-linked identifier only |
| ISO/IEC 42001:2023 AI management system                    | [ISO/IEC 42001:2023](https://www.iso.org/standard/42001)                                                                                                                                   |               2 |                 2 |                  100.0% | never pulled | source-linked identifier only |
| NIST AI Risk Management Framework                          | [NIST Artificial Intelligence Risk Management Framework (AI RMF 1.0)](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10)                       |               6 |                 6 |                  100.0% | never pulled | public-source citation        |
| PCI DSS v4.0 Payment Card Industry Data Security Standard  | [PCI Security Standards Council - PCI DSS v4.0](https://www.pcisecuritystandards.org/document_library/?category=pcidss)                                                                    |               3 |                 3 |                  100.0% | never pulled | source-linked identifier only |
| SOC 2 Trust Services Criteria                              | [AICPA & CIMA 2017 Trust Services Criteria (With Revised Points of Focus - 2022)](https://www.aicpa.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022) |               2 |                 2 |                  100.0% | never pulled | source-linked identifier only |

## Control-To-Asset Applicability

Every seeded control declares the asset types it can apply to. The pipeline uses
that catalog join to add `applicable_control_ids` to gold asset rows, so humans
and agents can ask "which controls apply to this asset?" without inferring from
labels or screenshots.

```bash
security-lakehouse controls applies-to --asset-type iam_role
```

Current seeded applicability:

| Asset type        | Applicable controls |
| ----------------- | ------------------: |
| `ai_agent`        |                  14 |
| `ai_model`        |                  14 |
| `service`         |                  11 |
| `data_store`      |                   9 |
| `host`            |                   7 |
| `audit_log`       |                   6 |
| `container_image` |                   6 |
| `s3_bucket`       |                   5 |
| `iam_role`        |                   4 |
| `identity_group`  |                   4 |
| `identity_user`   |                   4 |
| `okta_user`       |                   4 |
| `repo`            |                   4 |

## Readiness Gates

A framework tile is considered operationally trustworthy only when each gate is
true:

| Gate              | Evidence in repo                                                                                 |
| ----------------- | ------------------------------------------------------------------------------------------------ |
| Source linked     | `frameworks/registry.json` has official source URL, version, effective date, and sync cadence    |
| Control modeled   | `controls/catalog.json` has control ID, owner, evidence requirement, frequency, and rule         |
| Mapping reviewed  | `mappings/control_articles.json` links each control to official article/requirement references   |
| Rule versioned    | `evaluation_rule` points to a linted controls-as-code rule in `src/security_lakehouse/policy.py` |
| Coverage guarded  | `tests/test_mappings.py` enforces coverage floors for public-source frameworks                   |
| Runtime evaluated | pipeline emits gold `control_posture.jsonl` with rule reasons and evidence counts                |

## Official Marks And Logos

Framework names and product marks are not the same thing as certification
badges. TrustOps does not bundle official marks unless usage rights are
documented in [Third-Party Asset Policy](THIRD_PARTY_ASSETS.md). Product
screens and README visuals should use neutral text labels for framework scope
unless an approved asset entry exists with source URL, permitted-use terms,
attribution, owner, and review date.

This avoids three risks:

- implying TrustOps or a demo company is certified when it is not
- embedding protected certification seals in an open-source repo
- creating lookalike logos that appear official but are not

## Expansion Roadmap

| Track                    | Next target                                                                              | Notes                                              |
| ------------------------ | ---------------------------------------------------------------------------------------- | -------------------------------------------------- |
| Public-source frameworks | Increase NIST AI RMF, HIPAA, GDPR, and EU AI Act to 10+ controls each                    | Uses public official sources and reviewed mappings |
| Licensed frameworks      | Expand SOC 2, ISO, and PCI only from allowed identifiers and internal titles             | Do not reproduce licensed standard text            |
| Evidence requirements    | Add expected source types and freshness SLAs per control                                 | Feeds connector planning and confidence scoring    |
| Crosswalks               | Add reviewed shared-control mappings across frameworks                                   | Avoid heuristic-only equivalence claims            |
| UI                       | Show coverage percent, source freshness, and mapped-control count in the Frameworks page | Keep hero visuals clean; detailed truth lives here |
