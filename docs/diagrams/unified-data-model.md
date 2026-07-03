# Unified Data Model

Single-page view of **lake zones** (compliance truth), **application state** (server DB), and how API surfaces read them.

```mermaid
erDiagram
  %% --- Lake: bronze / silver / gold (JSONL + marts) ---
  RAW_EVENT {
    string event_id PK
    string tenant_id
    string raw_sha256
  }
  SILVER_EVENT {
    string event_id PK
    string asset_id
    string status
    string severity
    list control_ids
  }
  CONTROL_POSTURE {
    string control_id PK
    string framework
    string status
    int open_event_count
  }
  CONTROL_TEST {
    string test_id PK
    string control_id FK
    string result
  }
  VIOLATION {
    string violation_id PK
    string control_id
    string event_id
    string severity
  }
  SNAPSHOT {
    string assessment_hash PK
    datetime evaluated_at
  }

  RAW_EVENT ||--o{ SILVER_EVENT : normalizes
  SILVER_EVENT ||--o{ CONTROL_POSTURE : evaluates
  SILVER_EVENT ||--o{ VIOLATION : fails
  CONTROL_POSTURE ||--o{ CONTROL_TEST : programs
  CONTROL_POSTURE ||--o{ SNAPSHOT : freezes

  %% --- Application state (Postgres / SQLite) ---
  TENANT {
    string id PK
    string slug
    string name
  }
  USER {
    string id PK
    string tenant_id FK
    string email
    string role
  }
  TENANT_INVITE {
    string id PK
    string tenant_id FK
    string email
    string token_hash
    string status
  }
  API_KEY {
    string id PK
    string user_id FK
    string key_hash
  }
  REMEDIATION_TASK {
    string id PK
    string control_id
    string violation_id
  }
  AGENT_RUN {
    string id PK
    string harness
    string status
  }

  TENANT ||--o{ USER : members
  TENANT ||--o{ TENANT_INVITE : invites
  USER ||--o{ API_KEY : owns
  TENANT ||--o{ REMEDIATION_TASK : tracks
  TENANT ||--o{ AGENT_RUN : persists

  %% --- Cross-layer links (logical, not FK) ---
  REMEDIATION_TASK }o--|| VIOLATION : violation_id
  REMEDIATION_TASK }o--|| CONTROL_POSTURE : control_id
  AGENT_RUN }o..o{ CONTROL_POSTURE : reads_redacted
```

## Zone summary

| Zone | Storage | Writer | Primary consumers |
| ---- | ------- | ------ | ----------------- |
| **Raw / bronze** | `raw/`, `bronze/*.jsonl` | Connector sync (single writer) | Pipeline replay |
| **Silver** | `silver/normalized_events.jsonl` | Pipeline | Assessment, SOC harness |
| **Gold** | `gold/*.jsonl`, `current_posture.json` | Pipeline + assessment | Console, `/api/v1`, PDF export |
| **Snapshots** | `gold/snapshots/`, ledger | Assessment API | Audit, trust center point-in-time |
| **App DB** | `server/app.db` or Postgres | Server mode API | Auth, remediation, agents, invites |
| **Marts** | `mart/*.sqlite`, `*.duckdb` | Pipeline | Analytics CLI, optional BI |

## Read paths

```text
Console / API / MCP
  ├─ posture, controls, violations  → gold/ + silver/ (lake)
  ├─ auth, keys, sessions             → app DB
  ├─ remediation, evidence requests   → app DB (+ lake control_id refs)
  └─ agent runs                       → app DB (sanitized state, no raw lake path)
```

## Related docs

- [DATA_MODEL.md](../DATA_MODEL.md) — logical assessment entities
- [diagrams/data-model.md](data-model.md) — analytics mart tables
- [ARCHITECTURE.md](../ARCHITECTURE.md) — pipeline flow
- [DATA_FLOW.md](../DATA_FLOW.md) — ingestion → evaluation
