Frameworks: 10
Seeded controls: 607
Reviewed mappings: 607
Asset types modeled: 18
Control-to-asset applicability links: 2032
Seeded mapping coverage: 100.0%

| Framework                                                  | Official source                                                                                                                                                                                 | Seeded controls | Reviewed mappings | Seeded mapping coverage | Source state | Source policy                 |
| ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------: | ----------------: | ----------------------: | ------------ | ----------------------------- |
| CIS Amazon Web Services Foundations Benchmark              | [CIS Amazon Web Services Foundations Benchmark v3.0.0](https://www.cisecurity.org/benchmark/amazon_web_services)                                                                                |              62 |                62 |                  100.0% | never pulled | source-linked identifier only |
| EU AI Act - Regulation (EU) 2024/1689                      | [EUR-Lex - Regulation (EU) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)                                                                                                           |               6 |                 6 |                  100.0% | never pulled | public-source citation        |
| FedRAMP Moderate (NIST SP 800-53 Rev 5 Moderate baseline)  | [NIST SP 800-53 Rev 5 Moderate baseline (FedRAMP Moderate foundation)](https://csrc.nist.gov/publications/detail/sp/800-53b/final)                                                              |             287 |               287 |                  100.0% | never pulled | source-linked identifier only |
| GDPR - EU General Data Protection Regulation (2016/679)    | [EUR-Lex - Regulation (EU) 2016/679](https://eur-lex.europa.eu/eli/reg/2016/679/oj)                                                                                                             |               6 |                 6 |                  100.0% | never pulled | public-source citation        |
| HIPAA Security Rule (45 CFR Parts 160, 162, 164)           | [U.S. HHS HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/index.html)                                                                                                 |               6 |                 6 |                  100.0% | never pulled | public-source citation        |
| ISO/IEC 27001:2022 Information security management systems | [ISO/IEC 27001:2022](https://www.iso.org/standard/27001)                                                                                                                                        |              93 |                93 |                  100.0% | never pulled | source-linked identifier only |
| ISO/IEC 42001:2023 AI management system                    | [ISO/IEC 42001:2023](https://www.iso.org/standard/42001)                                                                                                                                        |              39 |                39 |                  100.0% | never pulled | source-linked identifier only |
| NIST AI Risk Management Framework                          | [NIST Artificial Intelligence Risk Management Framework (AI RMF 1.0)](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10)                            |              72 |                72 |                  100.0% | never pulled | public-source citation        |
| PCI DSS v4.0 Payment Card Industry Data Security Standard  | [PCI Security Standards Council - PCI DSS v4.0](https://www.pcisecuritystandards.org/document_library/?category=pcidss)                                                                         |               3 |                 3 |                  100.0% | never pulled | source-linked identifier only |
| SOC 2 Trust Services Criteria                              | [AICPA & CIMA 2017 Trust Services Criteria (With Revised Points of Focus - 2022)](https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022) |              33 |                33 |                  100.0% | never pulled | source-linked identifier only |

## Control-To-Asset Applicability

Every seeded control declares the asset types it applies to. The pipeline joins those declarations into gold asset rows as `applicable_control_ids`.

| Asset type                 | Applicable controls |
| -------------------------- | ------------------: |
| `service`                  |                 452 |
| `audit_log`                |                 193 |
| `cloud_policy`             |                 180 |
| `cloud_resource`           |                 180 |
| `iam_role`                 |                 134 |
| `data_store`               |                 126 |
| `ai_agent`                 |                 117 |
| `ai_model`                 |                 117 |
| `identity_user`            |                  76 |
| `identity_group`           |                  74 |
| `okta_user`                |                  74 |
| `s3_bucket`                |                  64 |
| `container_image`          |                  62 |
| `identity_account`         |                  61 |
| `repo`                     |                  60 |
| `host`                     |                  58 |
| `identity_role_assignment` |                   3 |
| `account_config`           |                   1 |
