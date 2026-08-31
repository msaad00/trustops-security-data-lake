# Internal Compliance Tool Vision

The product vision is a small internal trust automation platform for one
company. It should feel like an assessment and enablement layer for security
evidence, not a reporting wrapper.

The public category is:

> Open-source continuous risk and compliance assessment layer for existing
> security data lakes, internal evidence stores, humans, and coding agents.

The tool should be able to run in two modes:

| Mode                      | Best fit                                                                                                          |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| Existing lake mode        | read from a company's Snowflake, ClickHouse, object storage, SIEM, scanner, or ticketing data                     |
| Managed lake objects mode | create normalized tables, views, snapshots, and evidence objects when the company does not have a clean model yet |

## Core Jobs

1. **Assess posture continuously**
   - current framework scores
   - current control state
   - current violations
   - stale and missing evidence
   - owner and asset impact

2. **Freeze point-in-time snapshots**
   - audit evidence snapshots
   - vendor due-diligence snapshots
   - incident snapshots
   - board or executive snapshots
   - assessment hashes

3. **Inventory evidence sources**
   - cloud posture
   - vulnerability scanners
   - identity provider exports
   - runtime policy logs
   - SIEM alerts
   - remediation tickets
   - model registry and AI governance records

4. **Normalize evidence**
   - one event schema
   - one asset model
   - one control mapping model
   - evidence hashes and retained evidence references

5. **Map controls**
   - SOC 2, ISO 27001, CIS, PCI, and NIST AI RMF
   - owner, risk domain, evidence requirement, test logic, status, exceptions

6. **Continuously test controls**
   - pass/fail status
   - evidence freshness
   - open-risk count
   - owner queue
   - stale evidence and missing evidence alerts

7. **Operate remediation**
   - control owners
   - asset owners
   - SLA due dates
   - ticket references
   - exception state and expiry

8. **Prepare audits**
   - auditor evidence room
   - control-to-evidence traceability
   - immutable raw hashes
   - Snowflake governed evidence views
   - exportable packets

## Minimum Viable Internal Product

The first version should ship these product surfaces:

| Surface                 | Purpose                                                                         |
| ----------------------- | ------------------------------------------------------------------------------- |
| Current Posture API/CLI | continuously refreshed answer to "are we compliant right now?"                  |
| Snapshot API/CLI        | point-in-time assessment for audits, incidents, and just-in-time vendor reviews |
| Violations API/CLI      | open framework/control violations with owner, asset, evidence, and raw hash     |
| Agent API               | JSON routes for posture, violations, controls, assets, and snapshots            |
| TrustOps Overview       | executive posture, control gaps, evidence coverage, top risk asset              |
| Control Workbench       | risk-ranked controls, owners, pass/fail, evidence count                         |
| Evidence Room           | source event, asset, control, evidence reference, raw hash                      |
| Asset Risk Queue        | systems driving control gaps and remediation work                               |
| Data Lake Routing       | Snowflake for governed evidence, ClickHouse for telemetry analytics             |

## Continuous vs Point-In-Time Assessment

The system has two assessment modes:

| Mode                   | Question answered                                              | Artifact                                           |
| ---------------------- | -------------------------------------------------------------- | -------------------------------------------------- |
| Current posture        | "What is our accurate compliance and risk state right now?"    | `build/lakehouse/gold/current_posture.json`        |
| Point-in-time snapshot | "What did we know at this exact audit/vendor/incident moment?" | `build/lakehouse/gold/snapshots/assessment-*.json` |

Current posture should refresh whenever connectors ingest new evidence. A
snapshot freezes that posture with an assessment hash, reason, frameworks,
violations, stale controls, top risk assets, and evidence references.

Useful commands:

```bash
security-lakehouse assessment status --lake build/lakehouse
security-lakehouse assessment violations --lake build/lakehouse --framework "SOC 2"
security-lakehouse assessment snapshot \
  --lake build/lakehouse \
  --reason vendor_due_diligence
security-lakehouse serve --lake build/lakehouse --port 8787
```

Agent-friendly routes:

```text
GET  /api/posture/current
GET  /api/violations
GET  /api/controls
GET  /api/assets
POST /api/snapshots
```

## Data Model Additions To Build Next

```text
controls
  control_id
  framework
  title
  owner
  evidence_requirement
  test_query
  frequency
  risk_domain

evidence_items
  evidence_id
  source
  control_id
  asset_id
  uri
  collected_at
  expires_at
  raw_sha256

control_tests
  test_id
  control_id
  result
  evaluated_at
  failing_reason
  evidence_ids

assessment_snapshots
  assessment_hash
  assessment_type
  evaluated_at
  reason
  posture_state
  framework_scores
  violation_ids
  stale_controls

remediation_tasks
  task_id
  control_id
  asset_id
  owner
  status
  due_at
  ticket_url

exceptions
  exception_id
  control_id
  asset_id
  reason
  approver
  expires_at
```

## Why Snowflake And ClickHouse Both Matter

Snowflake is the audit and governance layer. It is where GRC, audit, leadership,
and compliance owners can query curated evidence with RBAC and retention.

ClickHouse is the security operations layer. It is where runtime events,
detections, and high-volume telemetry stay fast enough for investigations and
dashboards.

The internal tool sits above both:

```text
connectors -> normalized evidence -> control tests -> owner tasks -> audit room
                                      |                         |
                                      v                         v
                                ClickHouse                Snowflake
```
