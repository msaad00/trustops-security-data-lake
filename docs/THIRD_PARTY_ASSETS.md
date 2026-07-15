# Third-Party Asset Policy

TrustOps does not ship made-up framework logos, imitation certification seals,
regulator marks, or third-party trust badges.

Framework and compliance visuals should use project-owned icons and exact
official names unless an
official public brand or certification asset is added with:

- official source URL
- permitted-use terms or written permission
- required attribution
- file owner and review date

Certification marks must not be shown unless TrustOps or the displayed company
actually holds that certification and the mark usage terms permit the display.

## Current Asset Registry

| Asset family                                                                                               | Current repo status                                | Public rendering policy                                                                                            |
| ---------------------------------------------------------------------------------------------------------- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Framework labels such as SOC 2, ISO/IEC 27001, HIPAA, PCI DSS, GDPR, EU AI Act, NIST AI RMF, ISO/IEC 42001 | Exact names with project-owned icons               | Allowed when they identify framework scope and do not imply certification                                          |
| Official certification seals, regulator marks, and framework logos                                         | Not bundled except approved NIST framework artwork | Do not add until source, usage terms, attribution, owner, and review date are recorded here                        |
| Product logos for integrated tools and cloud providers                                                     | Not bundled by default                             | Prefer neutral source labels unless an integration doc requires the mark and permitted-use terms are recorded here |
| Connector brand logos (AWS, Azure, GCP, GitHub, Okta, Snowflake, Google, Jira, ClickHouse)                 | `connector-brand-logos.ts`                         | Integration tiles — Simple Icons (CC0) for monochrome marks; Google Cloud uses official multi-color brand paths    |
| Identity-provider marks (Okta, Entra ID, Google, SAML, API keys)                                           | Generated in `auth-visuals.ts`                     | Text abbreviations for login/access surfaces — not official IdP logos; see `AuthMark` component                    |

## Approved Official Assets

The following are framework illustrations, not agency logos or certification
seals. NIST does not endorse TrustOps or its control evaluations.

| Framework                              | Local asset                                  | Official source                                                                 | Terms                                                                         | Attribution          | Integrity                                    |
| -------------------------------------- | -------------------------------------------- | ------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | -------------------- | -------------------------------------------- |
| NIST Cybersecurity Framework (CSF) 2.0 | `app/web/public/frameworks/nist-csf-2.0.png` | [NIST image record](https://www.nist.gov/image/nist-cybersecurity-framework-20) | [NIST copyright and disclaimers](https://www.nist.gov/copyrights-disclaimers) | NIST/Natasha Hanacek | SHA-256 in `frameworks/identity-assets.json` |
| NIST AI Risk Management Framework 1.0  | `app/web/public/frameworks/nist-ai-rmf.png`  | [NIST image record](https://www.nist.gov/image/ai-risk-management-framework)    | [NIST copyright and disclaimers](https://www.nist.gov/copyrights-disclaimers) | N. Hanacek/NIST      | SHA-256 in `frameworks/identity-assets.json` |

The reviewed decision for every registered framework is recorded in
`frameworks/identity-assets.json`. ISO, AICPA SOC, CIS, FedRAMP, PCI SSC, HHS,
and EU institutional artwork is not bundled because its terms do not permit
generic OSS product use or because no official framework logo exists.
