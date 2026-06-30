# Diagram Index

Visual references for architecture, ingestion, auth, and deployment.

## Mermaid (in-repo)

| Diagram | File |
| ------- | ---- |
| Connector ingestion & read-only connections | [connector-ingestion.md](connector-ingestion.md) |
| OIDC / SAML / API key identity | [auth-identity.md](auth-identity.md) |
| OSS / self-hosted / hosted models | [deployment-models.md](deployment-models.md) |
| Local file-backed architecture | [architecture.md](architecture.md) |
| Dual lakehouse routing | [dual-lakehouse.md](dual-lakehouse.md) |
| Evaluation lifecycle | [evaluation-lifecycle.md](evaluation-lifecycle.md) |
| Hosting topology | [hosting.md](hosting.md) |
| Agent workflow | [agent-workflow.md](agent-workflow.md) |

## SVG (README & docs)

| Asset | Use |
| ----- | --- |
| [trustops-assessment-architecture.svg](../images/trustops-assessment-architecture.svg) | Continuous assessment hero |
| [trustops-readonly-connections.svg](../images/trustops-readonly-connections.svg) | Drata/Vanta-class read-only connect |
| [trustops-identity-boundary.svg](../images/trustops-identity-boundary.svg) | SSO + API key boundary |
| [trustops-product-mosaic.svg](../images/trustops-product-mosaic.svg) | Product surfaces |
| [trustops-readme-banner.svg](../images/trustops-readme-banner.svg) | README banner |

## Console diagrams

Interactive flow strips live in `app/web/src/components/diagrams/`:

- `IngestionPipelineDiagram` — `/connectors`
- `ConnectionCompareDiagram` — `/connectors`
- `AuthIdentityDiagram` — `/auth`
- `FlowStrip` — `/deploy` go-live path
