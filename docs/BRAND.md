# Koda Brand

**Koda** is an **open-source, headless-first trust operations platform**. Evidence
stays in the customer's lake, VPC, or laptop; posture, controls, workflows,
snapshots, and audit artifacts are exposed through the same API for console,
CI, agents, and runbooks.

## Name

**Koda** (Sioux: friend, ally) — your loyal trust partner in the lakehouse.
The otter mascot reflects that bond: read-only, customer-boundary evidence;
deterministic proof you can share with auditors.

| Use                    | Form                                                     |
| ---------------------- | -------------------------------------------------------- |
| Product / company      | **Koda**                                                 |
| Console UI             | **Koda Console**                                         |
| Public reviewer shares | **Koda Trust Center**                                    |
| Technical repo / PyPI  | `trustops-security-data-lake` (legacy package name)      |
| Operator CLI           | `security-lakehouse` (module path: `security_lakehouse`) |
| Legacy alias           | TrustOps — repo continuity only; not customer-facing     |

Do **not** use "Workbench", "Assessment Console", or "Security Lakehouse" as
customer-facing product names.

## Taglines

- **Category:** Open-source trust operations
- **Mission:** Turn evidence in your lake into live compliance posture,
  audit-ready snapshots, and shareable proof.
- **Surfaces:** API · CLI · MCP · CI · Console

## Logo

The Koda mark is a gradient square with a **river-otter mascot** (warm brown
fur, visible ink-black eyes and nose), **K monogram on the chest**, and a
**proof check badge** (deterministic verdict / audit proof).

| Token           | Value                                                      |
| --------------- | ---------------------------------------------------------- |
| Gradient start  | `#4f7cff`                                                  |
| Gradient end    | `#30c7d2`                                                  |
| Otter fur dark  | `#4a3420` (dorsal cap, ears)                               |
| Otter fur mid   | `#7a5c3a`                                                  |
| Otter fur light | `#e2c9a0` (cheeks)                                         |
| Muzzle / belly  | `#f5ead8` / `#faf3e8`                                      |
| Facial ink      | `#101623` (eyes, nose — keep high contrast at 16px)        |
| Proof badge     | White circle + `#047857` check (bottom-right of mark)      |
| Wordmark ink    | `#101623` on light UI; gradient or `#f8fafc` on dark rails |
| Corner radius   | 8px at 32×32 (scales with size)                            |

### Assets

| File                                            | Use                          |
| ----------------------------------------------- | ---------------------------- |
| `app/web/src/app/icon.svg`                      | Favicon (Next.js App Router) |
| `app/web/src/components/brand/KodaMark.tsx`     | In-app otter mark component  |
| `app/web/src/components/brand/TrustOpsLogo.tsx` | Monogram + wordmark lockup   |

### Usage rules

- Prefer the otter mark over a plain letter in UI chrome.
- On dark rails (sidebar, top bar), use the mark with white or light
  wordmark text — do not recolor the gradient.
- Do not stretch, rotate, or add drop shadows to the mark.
- Framework and connector logos follow [THIRD_PARTY_ASSETS.md](THIRD_PARTY_ASSETS.md).

## Typography

- **UI / wordmark:** Inter, weight 800–900 for product name
- **Body:** Inter, system-ui fallback stack (see `tailwind.config.ts`)

## Voice

- **Headless-first:** API and automation are primary; console is a peer surface.
- **Deterministic:** Controls and verdicts are code, not model guesses.
- **Customer-owned evidence:** Read-only ingestion; no vendor evidence silo.
- **Avoid competitor names** in repo copy, UI, docs, and PRs — use "managed GRC SaaS".

## Code reference

Brand constants for metadata and copy live in `app/web/src/lib/brand.ts`.

See also [VISUAL_SYSTEM.md](VISUAL_SYSTEM.md) for layout, KPI tiles, and marks.
