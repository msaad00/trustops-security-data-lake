# TrustOps Brand

TrustOps is an **open-source, headless-first trust operations platform**. Evidence
stays in the customer's lake, VPC, or laptop; posture, controls, workflows,
snapshots, and audit artifacts are exposed through the same API for console,
CI, agents, and runbooks.

## Name

| Use                    | Form                                                     |
| ---------------------- | -------------------------------------------------------- |
| Product / company      | **TrustOps** (one word, capital T and O)                 |
| Console UI             | **TrustOps Console**                                     |
| Public reviewer shares | **TrustOps Trust Center**                                |
| Technical repo / PyPI  | `trustops-security-data-lake`                            |
| Operator CLI           | `security-lakehouse` (module path: `security_lakehouse`) |

Do **not** use "Workbench", "Assessment Console", or "Security Lakehouse" as
customer-facing product names.

## Taglines

- **Category:** Open-source trust operations
- **Mission:** Turn evidence in your lake into live compliance posture,
  audit-ready snapshots, and shareable proof.
- **Surfaces:** API · CLI · MCP · CI · Console

## Logo

The TrustOps mark is a gradient square monogram with a white **T**.

| Token          | Value                           |
| -------------- | ------------------------------- |
| Gradient start | `#4f7cff`                       |
| Gradient end   | `#30c7d2`                       |
| Wordmark ink   | `#101623`                       |
| Corner radius  | 8px at 32×32 (scales with size) |

### Assets

| File                                            | Use                           |
| ----------------------------------------------- | ----------------------------- |
| `docs/images/trustops-logo.svg`                 | Docs, README, external slides |
| `app/web/src/app/icon.svg`                      | Favicon (Next.js App Router)  |
| `app/web/public/og/trustops-share.svg`          | Social / link preview card    |
| `app/web/src/components/brand/TrustOpsMark.tsx` | In-app monogram component     |
| `app/web/src/components/brand/TrustOpsLogo.tsx` | Monogram + wordmark lockup    |

### Usage rules

- Prefer the SVG monogram over a plain letter **T** in UI chrome.
- On dark rails (sidebar, top bar), use the monogram with white or light
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
- Avoid competitor names in repo copy, UI, docs, and PRs.

## Code reference

Brand constants for metadata and copy live in `app/web/src/lib/brand.ts`.

See also [VISUAL_SYSTEM.md](VISUAL_SYSTEM.md) for layout, KPI tiles, and marks.
