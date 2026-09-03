# Framework Coverage Matrix

Generated from the control catalog + CCF safeguards — never hand-edited.
Regenerate with `make coverage-doc`. `Attestable` is the auditor-defensible
coverage (reviewed safeguard mappings); the gap to `Evaluatable` is the
review backlog.

Frameworks: 15 (13 implemented, 2 planned)
Requirements catalogued: 942 (all source-cited)
Evaluatable (touched by a safeguard): 520 (55.2%)
**Attestable (reviewed safeguard mapping — what an auditor accepts): 45 (4.8%)**
Asset types modeled: 20

> `Source-cited` = the requirement has an official source link (always 100%). `Evaluatable` = a safeguard claims it (reviewed or proposed). `Attestable` = a human has confirmed the safeguard→requirement mapping — the only coverage an audit accepts. The gap between Evaluatable and Attestable is the review backlog.

| Framework | Official source | Status | Requirements | Source-cited | Evaluatable | Attestable | Attestable % | Source state |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| CIS Amazon Web Services Foundations Benchmark | [CIS Amazon Web Services Foundations Benchmark v3.0.0](https://www.cisecurity.org/benchmark/amazon_web_services) | implemented_full_pack | 62 | 62 | 49 | 2 | 3.2% | never pulled |
| CMMC 2.0 Level 2 (NIST SP 800-171 alignment) | [DoD CMMC Program](https://dodcio.defense.gov/CMMC/Documentation/) | implemented_full_pack | 110 | 110 | 103 | 0 | 0.0% | never pulled |
| EU AI Act - Regulation (EU) 2024/1689 | [EUR-Lex - Regulation (EU) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) | implemented_limited_mapping | 15 | 15 | 15 | 1 | 6.7% | never pulled |
| FedRAMP Moderate (NIST SP 800-53 Rev 5 Moderate baseline) | [NIST SP 800-53 Rev 5 Moderate baseline (FedRAMP Moderate foundation)](https://csrc.nist.gov/publications/detail/sp/800-53b/final) | implemented_full_pack | 287 | 287 | 177 | 4 | 1.4% | never pulled |
| GDPR - EU General Data Protection Regulation (2016/679) | [EUR-Lex - Regulation (EU) 2016/679](https://eur-lex.europa.eu/eli/reg/2016/679/oj) | implemented_limited_mapping | 20 | 20 | 12 | 3 | 15.0% | never pulled |
| HIPAA Security Rule (45 CFR Parts 160, 162, 164) | [U.S. HHS HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/index.html) | implemented_limited_mapping | 18 | 18 | 18 | 4 | 22.2% | never pulled |
| ISO/IEC 27001:2022 Information security management systems | [ISO/IEC 27001:2022](https://www.iso.org/standard/27001) | implemented_full_pack | 93 | 93 | 11 | 10 | 10.8% | never pulled |
| ISO/IEC 27017:2015 Cloud security controls | [ISO/IEC 27017:2015](https://www.iso.org/standard/43757.html) | implemented_full_pack | 47 | 47 | 24 | 0 | 0.0% | never pulled |
| ISO/IEC 27701:2019 Privacy information management | [ISO/IEC 27701:2019](https://www.iso.org/standard/71670.html) | planned | 0 | 0 | 0 | 0 | 0.0% | never pulled |
| ISO/IEC 42001:2023 AI management system | [ISO/IEC 42001:2023](https://www.iso.org/standard/42001) | implemented_full_pack | 39 | 39 | 26 | 1 | 2.6% | never pulled |
| NIST AI Risk Management Framework | [NIST Artificial Intelligence Risk Management Framework (AI RMF 1.0)](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10) | implemented_full_pack | 72 | 72 | 6 | 1 | 1.4% | never pulled |
| NIST Cybersecurity Framework (CSF) 2.0 | [NIST Cybersecurity Framework 2.0](https://www.nist.gov/cyberframework) | implemented_full_pack | 106 | 106 | 6 | 6 | 5.7% | never pulled |
| PCI DSS v4.0 Payment Card Industry Data Security Standard | [PCI Security Standards Council - PCI DSS v4.0](https://www.pcisecuritystandards.org/document_library/?category=pcidss) | implemented_limited_mapping | 12 | 12 | 12 | 3 | 25.0% | never pulled |
| SOC 1 Type II (ICFR) | [AICPA SOC 1 Reporting on Controls at a Service Organization](https://www.aicpa-cima.com/topic/audit-assurance/audit-and-assurance-greater-than-soc-2) | planned | 0 | 0 | 0 | 0 | 0.0% | never pulled |
| SOC 2 Trust Services Criteria | [AICPA & CIMA 2017 Trust Services Criteria (With Revised Points of Focus - 2022)](https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022) | implemented_full_pack | 61 | 61 | 61 | 10 | 16.4% | never pulled |

## Control-To-Asset Applicability

Every seeded control declares the asset types it applies to. The pipeline joins those declarations into gold asset rows as `applicable_control_ids`.

| Asset type | Applicable controls |
| --- | ---: |
| `service` | 719 |
| `audit_log` | 325 |
| `cloud_resource` | 248 |
| `cloud_policy` | 243 |
| `iam_role` | 186 |
| `data_store` | 175 |
| `identity_user` | 146 |
| `ai_model` | 126 |
| `identity_group` | 126 |
| `okta_user` | 126 |
| `ai_agent` | 119 |
| `host` | 113 |
| `container_image` | 89 |
| `repo` | 88 |
| `s3_bucket` | 66 |
| `identity_account` | 61 |
| `user` | 4 |
| `identity_role_assignment` | 3 |
| `network` | 2 |
| `account_config` | 1 |
