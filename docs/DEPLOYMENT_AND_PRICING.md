# Deployment and Pricing

TrustOps is an **open-source trust operations platform** you can run yourself or
have managed for you. The product goal is Drata/Vanta-class continuous compliance
— evidence ingestion, control tests, posture dashboards, trust-center sharing,
and agent APIs — without locking evidence in a vendor silo or paying
enterprise-GRC platform premiums.

## Deployment models

| Model | Who runs it | Best for | What you pay |
| ----- | ----------- | -------- | ------------ |
| **OSS local** | You, on a laptop or CI runner | Contributors, evaluators, pipeline proofs | $0 software; your time |
| **Self-hosted** | You, in your VPC / cluster | Teams that need data residency, custom connectors, and full control | $0 software license + your cloud/ops cost |
| **Managed hosted** | TrustOps operator (or your MSP) on dedicated or shared infra | Teams that want a live URL fast without running Kubernetes | Platform fee — typically a **fraction of Vanta/Drata** (see below) |

Evidence stays in **your boundary** in every model: local files, customer-owned
Snowflake/ClickHouse/DuckDB, or a tenant-scoped `/lake` volume on your cluster.
TrustOps is not a hosted evidence warehouse that copies your cloud posture into
an opaque SaaS database.

```text
Sources (AWS, Azure, GCP, GitHub, Okta, Snowflake, …)
  -> read-only connectors
  -> bronze / silver / gold lake (your storage)
  -> deterministic control tests + snapshots
  -> console, API, trust-center shares, agents
```

### OSS local

Fastest path to evaluate the product:

```bash
pip install -e ".[dev,server]"
security-lakehouse fixtures load --company fintech --out build/lakehouse
security-lakehouse serve --lake build/lakehouse --server --allow-insecure-no-auth --port 8787
```

Open `http://127.0.0.1:8787/console/dashboard/`. No account, no invoice.

### Self-hosted

Production shape: Helm chart on EKS/AKS/GKE (or Docker Compose for small pilots),
OIDC/SAML for humans, API keys for agents, persistent `/lake`, scheduler-driven
connector syncs, and token-scoped trust-center links.

| Component | Typical POC | Production hardening |
| --------- | ----------- | -------------------- |
| Runtime | Helm on a small managed cluster | Private nodes, workload identity, external secrets |
| Auth | One tenant, OIDC/SAML | SCIM lifecycle, enforced SSO, least-privilege RBAC |
| State | Encrypted PVC at `/lake` | Backup/restore, per-tenant prefixes |
| Evidence | Read-only cloud/service identities | Customer IaC owns roles, grants, rotation |

Runbook: [Shareable POC Hosting](SHAREABLE_POC_HOSTING.md),
[deploy/README.md](../deploy/README.md),
[Server Auth](SERVER_AUTH.md).

### Managed hosted

Managed hosted is the same TrustOps binary and chart — operated for you on
dedicated or isolated tenant infrastructure. You get a workspace URL, SSO,
connector onboarding, scheduler operations, and support; you do **not** give up
ownership of the evidence lake or warehouse projections.

**Shipped today (v0.2.0):** invite-only hosted POC patterns — Helm, server
auth, live connectors, demo kit, trust shares. Operators bootstrap tenants
manually.

**Roadmap for commercial hosted:** self-serve signup, SCIM, usage limits,
billing, and deeper connector UX. See [ROADMAP.md](../ROADMAP.md).

Evaluator flow: [Shareable Demo](SHAREABLE_DEMO.md).

## How TrustOps compares to Vanta and Drata

Vanta and Drata are excellent **managed compliance automation** products. They
optimize for speed-to-audit with polished onboarding, policy templates, auditor
workflows, and large integration marketplaces. Pricing is **custom and
sales-led** — neither publishes list prices.

Public buyer reports and transaction aggregates (Vendr, SOC2 auditor guides,
2025–2026) commonly cite these **annual platform** bands for a single framework
(e.g. SOC 2):

| Segment | Typical Vanta / Drata platform fee (est.) |
| ------- | ----------------------------------------- |
| Startup (&lt;50 employees, 1 framework) | ~$10k–$28k / year |
| Growth (50–200 employees, 1–2 frameworks) | ~$25k–$55k / year |
| Mid-market / multi-framework | ~$50k–$110k+ / year |
| Enterprise (500+, 4+ frameworks) | ~$100k–$250k+ / year |

Add-ons (trust center, vendor risk, extra frameworks, onboarding packages) and
**10–50% year-over-year renewal increases** are common negotiation points.
Platform fees are only part of total cost — auditors, pen tests, and internal
engineering time often dominate year-one spend.

### TrustOps cost positioning

TrustOps separates **software** from **operations**:

| Cost line | Self-hosted TrustOps | Managed hosted TrustOps (target) | Typical Vanta / Drata |
| --------- | -------------------- | -------------------------------- | --------------------- |
| Software license | **$0** (OSS) | Platform fee | Custom quote |
| Infrastructure | Your cluster + storage (~$150–$2k/mo at POC scale) | Included or pass-through | Included in SaaS |
| Evidence storage | Your Snowflake / lake / PVC | Your boundary or dedicated tenant volume | Vendor-operated |
| Integrations | Open connector catalog + your IaC | Same | Large managed marketplace |
| Auditor / pen test | Same third-party cost | Same | Same |

**Target:** managed hosted TrustOps at roughly **⅓–½** the annual platform TCO
of comparable Vanta/Drata scope for teams that already have (or want) a
customer-owned evidence lake. Exact hosted tiers will be published when billing
ships; contact the operator for POC/hosted quotes today.

**When Vanta/Drata is the better fit:** you want fully managed compliance
program operations, auditor marketplace, and policy content out of the box with
minimal platform engineering.

**When TrustOps is the better fit:** you want **controls-as-code**, deterministic
tests over your lake, agent/MCP APIs, warehouse-native evidence, self-hosting or
dedicated hosting, and cost that scales with **your** infra — not per-seat GRC
SaaS markup.

## Feature parity lens (honest)

| Capability | TrustOps v0.2.0 | Vanta / Drata |
| ---------- | --------------- | ------------- |
| Continuous control tests from live integrations | Yes (connectors + scheduler) | Yes |
| Executive dashboard + framework readiness | Yes | Yes |
| Trust center / customer sharing | Yes (scoped tokens) | Yes |
| Policy/policy-template library | Partial (controls-as-code) | Extensive |
| Auditor workflow / audit project management | Roadmap | Mature |
| Vendor risk questionnaires | Roadmap | Mature |
| Multi-tenant self-serve SaaS signup | Roadmap | Yes |
| OSS + self-hosted | **Yes** | No |
| Customer-owned evidence lake | **Yes** | Limited |

See [Release Readiness](RELEASE_READINESS.md) and [Product Walkthrough](PRODUCT_WALKTHROUGH.md)
for shipped vs planned detail.

## Choosing a path

```text
Need to fork, air-gap, or pass strict data-residency review?
  -> Self-hosted (Helm / your cloud)

Want a live demo link for evaluators this week?
  -> Managed hosted POC or local fixtures + SHAREABLE_DEMO.md

Already centralize security evidence in Snowflake or a SIEM lake?
  -> Existing-lake read mode + TrustOps assessment on top

Replacing Vanta/Drata entirely on day one?
  -> Plan a phased migration: connectors + control parity first, auditor
     workflows and policy content second
```

## Next steps

| Goal | Doc |
| ---- | --- |
| Run locally in 5 minutes | [README.md](../README.md#run-locally) |
| Host a shareable POC | [SHAREABLE_POC_HOSTING.md](SHAREABLE_POC_HOSTING.md) |
| Evaluator demo script | [SHAREABLE_DEMO.md](SHAREABLE_DEMO.md) |
| Framework packs (SOC 2, NIST AI RMF, custom) | [FRAMEWORK_PACKS.md](FRAMEWORK_PACKS.md) |
| Architecture | [ARCHITECTURE.md](ARCHITECTURE.md) |

For hosted POC or enterprise self-hosted support inquiries, open a GitHub
discussion or issue on the repository.
