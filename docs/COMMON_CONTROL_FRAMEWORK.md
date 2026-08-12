# Common Control Framework

A Common Control Framework consolidates many regulatory requirements into one set
of operational safeguards. You operate the safeguard; framework coverage is
derived from it.

TrustOps is adopting this model. This document describes the target, what exists
today, and how the rest gets there.

## Why the catalog alone is not a CCF

`controls/catalog.json` is framework-first: 942 requirements, each carrying its
own `framework_id` **and its own `evidence_requirement`** — 942 distinct evidence
statements for 942 controls, none shared.

That last number is the whole problem. Because no two requirements share an
evidence statement, answering SOC 2, ISO 27001, and FedRAMP means answering the
same operational question three times, in three places, with three review trails.

`mappings/framework_equivalence.json` was a first attempt at relief, linking
requirements that address the same theme. But it is a crosswalk _laid over_ a
framework-first catalog. It annotates the duplication instead of removing it.

## The model

A **safeguard** is the operated object. It carries one evidence requirement, one
evaluation rule, one owner — and it satisfies many framework requirements.

```
safeguard  SG-IDENTITY-001  "Logical access and MFA"
  evidence_requirement   (one statement, operated once)
  evaluation_rule        (one test)
  satisfies
    SOC2-CC6.1            soc2              primary
    ISO27001-A.5.15       iso-27001-2022    equivalent
    NIST-CSF-PR.AA-01     nist-csf-2.0      equivalent
    FEDRAMP-AC-2          fedramp-moderate  equivalent
    CIS-AWS-1.10          cis_aws           equivalent
    HIPAA-164.308(a)(4)   hipaa-security-rule equivalent
```

Six requirements, one thing to operate.

### The relationship is many-to-many, in both directions

One safeguard satisfying many requirements is the point. The reverse also
happens: **SOC2 CC7.2 and PCI-DSS-10 each need two safeguards** — detection _and_
audit logging.

That forces a semantic decision, and it is the one worth arguing about:

> A framework requirement is met only when **every** safeguard mapped to it passes.

The alternative — any one passing is enough — would let a green logging safeguard
report a monitoring requirement as satisfied. That is a false attestation reaching
an auditor, which is the failure this system exists to prevent.

`requirement_status()` also distinguishes **`unmapped`** from `fail`. "We have not
modelled this yet" and "we tested it and it failed" are different answers, and
collapsing them would overstate both coverage and failure.

## Where it stands

Twelve safeguards, promoted from the twelve curated equivalence groups:

```
$ security-lakehouse frameworks safeguards --format table
12 safeguards cover 45 of 942 requirements (4.8%)
```

| Framework           | Requirements | Covered |
| ------------------- | -----------: | ------: |
| fedramp-moderate    |          287 |       4 |
| cmmc-2-level2       |          110 |   **0** |
| nist-csf-2.0        |          106 |       6 |
| iso-27001-2022      |           93 |      10 |
| nist-ai-rmf         |           72 |       1 |
| cis_aws             |           62 |       2 |
| soc2                |           61 |      10 |
| iso-27017-2015      |           47 |   **0** |
| iso-42001-2023      |           39 |       1 |
| gdpr-2016-679       |           20 |       3 |
| hipaa-security-rule |           18 |       4 |
| eu-ai-act-2024-1689 |           15 |       1 |
| pci-dss-v4          |           12 |       3 |

Two frameworks are at zero, so adopting them today inherits nothing from work
already done for SOC 2 or ISO 27001.

## The ceiling is not 100%

Of the 897 unmapped requirements, **78 have no equivalent in any other
framework** — their risk domain appears in exactly one framework. Mostly NIST AI
RMF (36), SOC 2 (24), GDPR (10), EU AI Act (4), PCI (3), ISO 27001 (1).

Those become **single-requirement safeguards**: still worth modelling, because the
safeguard is what gets operated, but they consolidate nothing.

So the realistic target is roughly **864 of 942 requirements mapped (~92%)**,
across an expected few hundred safeguards. Forcing the last 78 into shared
safeguards would assert equivalences that do not exist.

## Getting there

1. **Model** — `controls/safeguards.json`, validated, with coverage derived from
   data. _Done._
2. **Curate** — grow the safeguard set toward the ~92% ceiling. Judgment per
   safeguard; `validate_safeguards()` catches structural errors, not semantic
   ones. A wrong equivalence is invisible until an auditor rejects the evidence.
3. **Invert the engine** — evaluate safeguards, derive requirement status through
   `requirement_status()`, and let framework readiness fall out of that rather
   than being computed alongside it.
4. **Retire the overlay** — once safeguards subsume it,
   `mappings/framework_equivalence.json` and the `/crosswalk` surface it feeds
   become a view over the CCF instead of a parallel source of truth.

Steps 1 and 2 change no behaviour: coverage is reported, nothing is evaluated
through it yet. Step 3 is where posture starts flowing through safeguards, and it
needs the curation from step 2 to be worth switching on.

## Schema

`controls/safeguards.json`, `schema: trustops.safeguards.v1`.

| Field                  | Meaning                                                       |
| ---------------------- | ------------------------------------------------------------- |
| `safeguard_id`         | `SG-<RISKDOMAIN>-<NNN>`, stable                               |
| `title`                | What the safeguard does                                       |
| `risk_domain`          | Shared taxonomy with the control catalog                      |
| `objective`            | Why these requirements are genuinely the same thing           |
| `evidence_requirement` | The single statement this safeguard proves                    |
| `evaluation_rule`      | The single test                                               |
| `owner`, `frequency`   | Who operates it, how often                                    |
| `satisfies[]`          | `control_id`, `framework_id`, `role` (`primary`/`equivalent`) |

Exactly one member carries `role: primary` — the requirement whose wording the
safeguard is drafted against. Every `control_id` must exist in the catalog; the
validator rejects claimed coverage that does not resolve.
