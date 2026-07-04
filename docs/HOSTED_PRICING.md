# Hosted Pricing Tiers

Published annual list prices for **managed hosted TrustOps**. Self-hosted OSS
remains **$0 software license** — you pay only your infrastructure.

> Target positioning: roughly **⅓–½** the annual platform TCO of comparable
> managed GRC scope for teams that keep a customer-owned evidence lake.

## Tiers

| Tier           | Annual (USD) | Users | API keys | Connectors | SCIM |
| -------------- | -----------: | ----: | -------: | ---------: | ---- |
| **Starter**    |       $4,800 |     5 |       10 |          2 | No   |
| **Team**       |      $12,000 |    25 |       50 |         10 | No   |
| **Business**   |      $28,000 |   100 |      200 |         50 | Yes  |
| **Enterprise** |       Custom |  10k+ |     10k+ |       10k+ | Yes  |

### Starter — $4,800 / year

Evaluator workspace and small-team POC.

- Hosted workspace URL
- OIDC / SAML SSO
- 2 live connectors
- Trust-center shares
- Community support

### Team — $12,000 / year

Production pilot for one framework program.

- Everything in Starter
- 10 connectors + scheduler
- Workflow automation
- Agent harness + MCP
- Email support (business hours)

### Business — $28,000 / year

Multi-framework GRC with SCIM lifecycle.

- Everything in Team
- SCIM 2.0 provisioning
- Vendor risk + policy library
- HA read-replica guidance
- Priority support

### Enterprise — custom

Dedicated tenant, custom SLAs, and air-gap options.

- Dedicated or isolated cluster
- Custom framework packs
- Customer success + onboarding

## API

Public (no auth):

```http
GET /api/v1/platform/pricing
```

Returns tier metadata, limits, and feature lists for console and sales tooling.

## Self-serve signup

Enable on hosted operators:

```bash
export TRUSTOPS_COMMERCIAL_HOSTED=1
export TRUSTOPS_SELF_SERVE_SIGNUP=1
export TRUSTOPS_SIGNUP_SECRET=<optional-abuse-guard>
```

```http
POST /api/v1/signup
X-TrustOps-Signup-Secret: <secret when configured>
Content-Type: application/json

{
  "org_slug": "acme",
  "org_name": "Acme Corp",
  "admin_email": "admin@acme.com",
  "plan_tier": "starter"
}
```

## Usage limits

When `TRUSTOPS_COMMERCIAL_HOSTED=1`, plan limits apply to users, API keys, and
pending invites. Admins can inspect usage:

```http
GET /api/v1/platform/usage
Authorization: Bearer <admin-api-key>
```

Billing integration (Stripe/invoicing) is not included in v0.2.x — limits are
enforced in-app; payment is operator-managed until billing ships.

## Related

- [COMMERCIAL_HOSTED.md](COMMERCIAL_HOSTED.md) — invites, email, SCIM scaffold
- [DEPLOYMENT_AND_PRICING.md](DEPLOYMENT_AND_PRICING.md) — OSS vs hosted positioning
- Console: `/console/pricing/`
