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

```
$ security-lakehouse frameworks safeguards --format table
20 safeguards map 465 of 942 requirements (49.4%) — 45 reviewed (4.8%), 420 proposed
```

A mapping is **reviewed** once a human has confirmed the requirements are the
same obligation. **Proposed** mappings were matched by title theme and are
reported separately, because a compliance product must never count unconfirmed
work as attested coverage. `safeguards_by_requirement(reviewed_only=True)` is
what attestation should read.

Curation is ordered by what teams are actually audited and certified against,
so the frameworks a customer arrives with are covered first.

| Framework           | Requirements | Mapped |   Pct |
| ------------------- | -----------: | -----: | ----: |
| eu-ai-act-2024-1689 |           15 |     13 | 86.7% |
| pci-dss-v4          |           12 |     10 | 83.3% |
| cmmc-2-level2       |          110 |     87 | 79.1% |
| soc2                |           61 |     46 | 75.4% |
| cis_aws             |           62 |     45 | 72.6% |
| hipaa-security-rule |           18 |     12 | 66.7% |
| iso-42001-2023      |           39 |     26 | 66.7% |
| gdpr-2016-679       |           20 |     12 | 60.0% |
| fedramp-moderate    |          287 |    167 | 58.2% |
| iso-27017-2015      |           47 |     24 | 51.1% |
| iso-27001-2022      |           93 |     11 | 11.8% |
| nist-ai-rmf         |           72 |      6 |  8.3% |
| nist-csf-2.0        |          106 |      6 |  5.7% |

### `cis_aws` is a benchmark, not the CIS Controls

Worth stating plainly, because the two are routinely conflated and the numbers
above would otherwise be read wrong.

- **CIS Controls v8** — 18 vendor-neutral, organization-level safeguards
  ("Inventory and Control of Enterprise Assets"). A framework you are assessed
  against. **Not in this catalog.**
- **CIS Benchmarks** — per-platform hardening guides, one per technology. The
  catalog carries exactly one: the **CIS Amazon Web Services Foundations
  Benchmark v3.0.0** (`cis_aws`, 62 recommendations). No Azure, GCP, or
  Kubernetes benchmark is present, though connectors exist for those clouds.

So a `cis_aws` percentage describes one cloud's hardening posture. It is not
CIS Controls coverage, and should never be quoted as such.

## The real ceiling is the catalog, not the curation

262 of 942 titles (28%) still carry no content — an
identifier plus boilerplate. `frameworks enrich` has already filled the FedRAMP
set from NIST SP 800-53 Rev. 5, recording the source URL and SHA-256 on every
control so the import is checkable rather than asserted.

What remains cannot be filled the same way:

- **ISO (82)** — the registry's guardrail is explicit that ISO text is
  licensed, so identifiers and short internal titles are the correct shape.
  Mapping ISO _ids_ into safeguards is still fine; it reproduces nothing.
- **NIST CSF (106)** — public domain, but its OSCAL catalog titles each
  subcategory with its own identifier (`GV.OC-01` is titled "GV.OC-01"). The
  importer rejects a title that merely repeats the id, because coverage that
  looks enriched while saying nothing is worse than an honest placeholder.
- **NIST AI RMF (66)** — no OSCAL catalog is published.

So 680 of 942 controls now carry curatable content, and the rest need
either a published crosswalk or a human with the source document.

## Getting there

Full coverage needs the catalog enriched before the curation can be checked.

1. **Model** — safeguards are the operated object, validated, coverage derived
   from data. _Done._
2. **Curate what is checkable** — the 393 requirements whose titles carry
   content. 216 are mapped; the rest are the near-term queue. Promoting a
   `proposed` mapping to `reviewed` is a human confirming the two requirements
   are the same obligation. _In progress._
3. **Enrich the 549 placeholder titles**, or import an authoritative crosswalk.
   NIST publishes 800-53 ↔ CSF mappings, CMMC L2 is NIST 800-171 with a
   published 800-53 mapping, and ISO ↔ NIST crosswalks exist. Importing those
   is how FedRAMP, CSF and ISO 27001 become curatable — and an imported
   crosswalk is checkable against its source, which invented equivalences never
   are.
4. **Invert the engine** — evaluate safeguards, derive requirement status via
   `requirement_status()`, let framework readiness fall out of that.
5. **Retire the overlay** — `mappings/framework_equivalence.json` and the
   `/crosswalk` surface become views over the CCF rather than a second source
   of truth.

Steps 1–3 change no behaviour: coverage is reported, nothing is evaluated
through it. Step 4 is where posture starts flowing through safeguards, and it
should not switch on until the mappings it depends on are `reviewed`.

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
