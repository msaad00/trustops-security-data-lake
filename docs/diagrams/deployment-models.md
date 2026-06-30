# Deployment Models

OSS local, self-hosted, and managed hosted — same product, different ops boundary.

```mermaid
flowchart TB
  subgraph OSS["OSS local — $0 license"]
    LAP["Laptop / CI"]
    FIX["Fixtures + SQLite"]
    DEMO["Console demo"]
  end

  subgraph SH["Self-hosted — your infra"]
    HELM["Helm on EKS/AKS/GKE"]
    PVC["/lake PVC"]
    SSO["Your OIDC/SAML"]
    SCHED["Scheduler CronJob"]
  end

  subgraph MH["Managed hosted — operator run"]
    URL["Workspace URL"]
    OP["Operator SSO + connectors"]
    TEN["Dedicated tenant volume"]
  end

  subgraph Evidence["Evidence always customer-scoped"]
    LAKE["Bronze / silver / gold"]
    WH["Snowflake / ClickHouse optional"]
  end

  OSS --> LAKE
  SH --> LAKE
  MH --> LAKE
  LAKE --> WH
```

## Cost boundary vs GRC SaaS

```mermaid
quadrantChart
  title Deployment flexibility vs platform TCO
  x-axis Low vendor lock-in --> High vendor lock-in
  y-axis Low platform fee --> High platform fee
  quadrant-1 Premium managed
  quadrant-2 Typical managed GRC SaaS
  quadrant-3 OSS self-hosted
  quadrant-4 Hosted alternative
  TrustOps self-hosted: [0.2, 0.15]
  TrustOps managed target: [0.35, 0.35]
  Managed GRC SaaS: [0.85, 0.8]
```

See [DEPLOYMENT_AND_PRICING.md](../DEPLOYMENT_AND_PRICING.md).
