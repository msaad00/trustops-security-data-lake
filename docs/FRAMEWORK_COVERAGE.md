Frameworks: 13 (13 implemented, 0 planned)
Seeded controls: 898
Reviewed mappings: 898
Asset types modeled: 18
Control-to-asset applicability links: 2911
Seeded mapping coverage: 100.0%

| Framework                                                  | Official source                                                                                                                                                                                 | Status                      | Seeded controls | Reviewed mappings | Seeded mapping coverage | Source state | Source policy                 |
| ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- | --------------: | ----------------: | ----------------------: | ------------ | ----------------------------- |
| CIS Amazon Web Services Foundations Benchmark              | [CIS Amazon Web Services Foundations Benchmark v3.0.0](https://www.cisecurity.org/benchmark/amazon_web_services)                                                                                | implemented_full_pack       |              62 |                62 |                  100.0% | never pulled | source-linked identifier only |
| CMMC 2.0 Level 2 (NIST SP 800-171 alignment)               | [DoD CMMC Program](https://dodcio.defense.gov/CMMC/Documentation/)                                                                                                                              | implemented_full_pack       |             110 |               110 |                  100.0% | never pulled | source-linked identifier only |
| EU AI Act - Regulation (EU) 2024/1689                      | [EUR-Lex - Regulation (EU) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)                                                                                                           | implemented_limited_mapping |               6 |                 6 |                  100.0% | never pulled | public-source citation        |
| FedRAMP Moderate (NIST SP 800-53 Rev 5 Moderate baseline)  | [NIST SP 800-53 Rev 5 Moderate baseline (FedRAMP Moderate foundation)](https://csrc.nist.gov/publications/detail/sp/800-53b/final)                                                              | implemented_full_pack       |             287 |               287 |                  100.0% | never pulled | source-linked identifier only |
| GDPR - EU General Data Protection Regulation (2016/679)    | [EUR-Lex - Regulation (EU) 2016/679](https://eur-lex.europa.eu/eli/reg/2016/679/oj)                                                                                                             | implemented_limited_mapping |               6 |                 6 |                  100.0% | never pulled | public-source citation        |
| HIPAA Security Rule (45 CFR Parts 160, 162, 164)           | [U.S. HHS HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/index.html)                                                                                                 | implemented_limited_mapping |               6 |                 6 |                  100.0% | never pulled | public-source citation        |
| ISO/IEC 27001:2022 Information security management systems | [ISO/IEC 27001:2022](https://www.iso.org/standard/27001)                                                                                                                                        | implemented_full_pack       |              93 |                93 |                  100.0% | never pulled | source-linked identifier only |
| ISO/IEC 27017:2015 Cloud security controls                 | [ISO/IEC 27017:2015](https://www.iso.org/standard/43757.html)                                                                                                                                   | implemented_full_pack       |              47 |                47 |                  100.0% | never pulled | source-linked identifier only |
| ISO/IEC 42001:2023 AI management system                    | [ISO/IEC 42001:2023](https://www.iso.org/standard/42001)                                                                                                                                        | implemented_full_pack       |              39 |                39 |                  100.0% | never pulled | source-linked identifier only |
| NIST AI Risk Management Framework                          | [NIST Artificial Intelligence Risk Management Framework (AI RMF 1.0)](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10)                            | implemented_full_pack       |              72 |                72 |                  100.0% | never pulled | public-source citation        |
| NIST Cybersecurity Framework (CSF) 2.0                     | [NIST Cybersecurity Framework 2.0](https://www.nist.gov/cyberframework)                                                                                                                         | implemented_full_pack       |             106 |               106 |                  100.0% | never pulled | public-source citation        |
| PCI DSS v4.0 Payment Card Industry Data Security Standard  | [PCI Security Standards Council - PCI DSS v4.0](https://www.pcisecuritystandards.org/document_library/?category=pcidss)                                                                         | implemented_limited_mapping |               3 |                 3 |                  100.0% | never pulled | source-linked identifier only |
| SOC 2 Trust Services Criteria                              | [AICPA & CIMA 2017 Trust Services Criteria (With Revised Points of Focus - 2022)](https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022) | implemented_full_pack       |              61 |                61 |                  100.0% | never pulled | source-linked identifier only |

## Control-To-Asset Applicability

Every seeded control declares the asset types it applies to. The pipeline joins those declarations into gold asset rows as `applicable_control_ids`.

| Asset type                 | Applicable controls |
| -------------------------- | ------------------: |
| `service`                  |                 691 |
| `audit_log`                |                 325 |
| `cloud_resource`           |                 248 |
| `cloud_policy`             |                 243 |
| `iam_role`                 |                 186 |
| `data_store`               |                 166 |
| `identity_user`            |                 146 |
| `identity_group`           |                 126 |
| `okta_user`                |                 126 |
| `ai_agent`                 |                 117 |
| `ai_model`                 |                 117 |
| `host`                     |                 113 |
| `container_image`          |                  89 |
| `repo`                     |                  87 |
| `s3_bucket`                |                  66 |
| `identity_account`         |                  61 |
| `identity_role_assignment` |                   3 |
| `account_config`           |                   1 |
