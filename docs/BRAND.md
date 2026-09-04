# Trust Data Lake brand

**Trust Data Lake** is the customer-facing product name. The repository, package, CLI, environment variables, API identifiers, and MCP commands retain their existing technical names for compatibility.

| Use                  | Form                             |
| -------------------- | -------------------------------- |
| Product              | **Trust Data Lake**              |
| Console              | **Trust Data Lake Console**      |
| Reviewer shares      | **Trust Data Lake Trust Center** |
| Repository / package | `trustops-security-data-lake`    |
| Operator CLI         | `security-lakehouse`             |
| MCP command          | `trustops-mcp`                   |

Do not introduce alternate customer-facing product names. Do not use “Workbench” or “Assessment Console” as the brand. “TrustOps” remains a technical compatibility identifier only.

## Positioning

- **Category:** open evidence infrastructure for GRC
- **Promise:** continuous compliance in your cloud
- **Differentiator:** customer-owned evidence, deterministic controls, one contract across Console · API · CLI · MCP · CI

## Visual identity

The primary mark is a cloud, agent spark, and identity glyph above lake contours on a deep-navy field. It must remain legible at 16 px and must not use letter monograms, generic shields, database stacks, or certification checks.

| Token     | Value                 |
| --------- | --------------------- |
| Gradient  | `#4f7cff` → `#30c7d2` |
| Ink       | `#101623`             |
| Dark rail | `#07111e`             |
| Lake line | `#5eead4`             |
| Wordmark  | Inter, 800–900        |

Primary assets:

- `docs/images/trustops-logo.svg` — documentation lockup
- `app/web/src/app/icon.svg` — favicon
- `app/web/src/components/brand/TrustOpsMark.tsx` — UI mark
- `app/web/src/components/brand/TrustOpsLogo.tsx` — UI lockup
- `app/web/public/og/trustops-share.svg` — social preview

Do not stretch, rotate, shadow, or recolor the mark. Framework and connector logos follow [THIRD_PARTY_ASSETS.md](THIRD_PARTY_ASSETS.md).

## Voice

- Direct and operational.
- Explain the evidence boundary before the feature list.
- Say what is deterministic, what is model-assisted, and what requires approval.
- Prefer concrete verbs: collect, evaluate, fix, prove.
- Use “managed GRC SaaS” instead of competitor names.

Brand constants live in `app/web/src/lib/brand.ts`. Layout and component guidance lives in [VISUAL_SYSTEM.md](VISUAL_SYSTEM.md).
