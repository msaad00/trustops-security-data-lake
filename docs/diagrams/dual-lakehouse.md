# Dual Lakehouse Architecture

```mermaid
flowchart TB
  subgraph Sources["Security + Compliance Sources"]
    Cloud["Cloud CSPM"]
    Vuln["Vulnerability Scans"]
    Runtime["Runtime Gateway"]
    Idp["Identity Provider"]
    Audit["Audit Log"]
    Siem["SIEM Alerts"]
    Tickets["Remediation Tickets"]
    Models["AI Model Registry"]
  end

  subgraph Local["Portable Local Pipeline"]
    Raw["Raw JSONL"]
    Bronze["Bronze<br/>raw + sha256"]
    Silver["Silver<br/>normalized_events"]
    Gold["Gold<br/>control_posture<br/>asset_risk<br/>metrics"]
    SQLite["SQLite Mart<br/>demo + tests"]
  end

  subgraph Snowflake["Snowflake Governed Evidence Lake"]
    SnowRaw["SECURITY_BRONZE.RAW_EVENTS"]
    SnowEvents["SECURITY_SILVER.NORMALIZED_EVENTS"]
    SnowControls["SECURITY_GOLD.CONTROL_POSTURE"]
    SnowAssets["SECURITY_GOLD.ASSET_RISK"]
    SnowViews["Audit / GRC Views"]
  end

  subgraph ClickHouse["ClickHouse Telemetry Analytics Lake"]
    ChEvents["security.normalized_events"]
    ChControls["security.control_posture"]
    ChAssets["security.asset_risk"]
    ChDash["Dashboard Aggregates"]
  end

  subgraph Apps["Consumption Layer"]
    Dashboard["Static Dashboard"]
    SQL["SQL Query CLI"]
    Agent["Compliance Analytics Agent Skill"]
    Auditor["Evidence Review"]
    SecOps["SecOps Investigation"]
  end

  Sources --> Raw
  Raw --> Bronze --> Silver --> Gold --> SQLite
  Gold --> Dashboard
  SQLite --> SQL
  SQLite --> Agent

  Bronze --> SnowRaw --> SnowEvents --> SnowControls --> SnowViews --> Auditor
  SnowEvents --> SnowAssets --> SnowViews

  Silver --> ChEvents --> ChDash --> SecOps
  Gold --> ChControls
  Gold --> ChAssets
  ChDash --> Dashboard
```

## Backend Split

Snowflake carries the governed evidence story. ClickHouse carries the telemetry
speed story. The local file-backed pipeline proves the transformation and model
without needing either service running.
