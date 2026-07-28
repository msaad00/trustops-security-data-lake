# TrustOps brand

**TrustOps** is the only customer-facing product name. “Security data lake” describes the architecture; it is not a second brand.

| Use                  | Form                          |
| -------------------- | ----------------------------- |
| Product              | **TrustOps**                  |
| Console              | **TrustOps Console**          |
| Reviewer shares      | **TrustOps Trust Center**     |
| Repository / package | `trustops-security-data-lake` |
| Operator CLI         | `security-lakehouse`          |
| MCP command          | `trustops-mcp`                |

Do not introduce alternate product names. Do not use “Workbench,” “Assessment Console,” or “Security Lakehouse” as a customer-facing brand.

## Positioning

- **Category:** open-source trust operations
- **Promise:** continuous compliance in your cloud
- **Differentiator:** customer-owned evidence, deterministic controls, one contract across Console · API · CLI · MCP · CI

## Visual identity

The primary mark is a blue-to-cyan rounded square with a white **T** and a green proof check. It must remain legible at 16 px.

| Token       | Value                 |
| ----------- | --------------------- |
| Gradient    | `#4f7cff` → `#30c7d2` |
| Ink         | `#101623`             |
| Dark rail   | `#07111e`             |
| Proof check | `#047857`             |
| Wordmark    | Inter, 800–900        |

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
