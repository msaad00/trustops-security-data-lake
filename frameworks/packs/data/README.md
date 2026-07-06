# Pack source data

Static identifier lists used by `security-lakehouse frameworks sync-packs`.

| File                             | Pack               | Count |
| -------------------------------- | ------------------ | ----: |
| `nist_800_53_rev5_moderate.json` | `fedramp-moderate` |   287 |
| `cis_aws_v3.json`                | `cis-aws`          |    62 |
| `cmmc_2_level2.json`             | `cmmc-2-level2`    |   110 |
| `iso_27017_2015.json`            | `iso-27017-2015`   |    47 |

ISO 27001 and ISO 42001 Annex A controls are generated programmatically in `src/security_lakehouse/pack_data.py`.

FedRAMP pack data is the NIST SP 800-53 Rev 5 **Moderate baseline** from NIST
OSCAL (`NIST_SP-800-53_rev5_MODERATE-baseline_profile.json`). FedRAMP Rev 5
Moderate authorization selects 323 controls with overlays; the delta ships in a
follow-up pack.
