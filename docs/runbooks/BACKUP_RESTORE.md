# Backup And Restore Runbook

TrustOps splits durable state into two places:

```text
TRUSTOPS_LAKE (/lake)
  ├── bronze/ silver/ gold/     <- compliance truth (evidence, posture, snapshots)
  ├── gold/connector_runs.jsonl <- sync/probe/discover history
  ├── gold/connector_config.jsonl
  ├── gold/scheduler_state.jsonl
  └── server/app.db             <- application-state DB (default SQLite)

TRUSTOPS_DATABASE_URL (optional)
  └── Postgres (or other SQLAlchemy URL) replaces server/app.db
```

Back up **both** the lake directory and the application-state database. Restoring
only one leaves the console, remediation queue, agent runs, and API keys out of
sync with posture and evidence.

## What To Back Up

| Path / object                              | Contents                                                       | RPO guidance                      |
| ------------------------------------------ | -------------------------------------------------------------- | --------------------------------- |
| `$TRUSTOPS_LAKE/bronze/`                   | Immutable raw evidence replay                                  | Same as lake                      |
| `$TRUSTOPS_LAKE/silver/`                   | Normalized evidence facts                                      | Same as lake                      |
| `$TRUSTOPS_LAKE/gold/`                     | Posture, controls, snapshots, connector state, workflows       | Same as lake                      |
| `$TRUSTOPS_LAKE/gold/connector_runs.jsonl` | Probe/sync/discover run history                                | Same as lake                      |
| `$TRUSTOPS_LAKE/server/app.db`             | Tenants, users, API keys, tasks, evidence requests, agent runs | Same as DB backup                 |
| Kubernetes Secret refs                     | Session secret, OIDC, Snowflake key mounts                     | Independent secret-manager backup |

Catalog files (`controls/`, `connectors/`, `frameworks/`) ship inside the
container image (`TRUSTOPS_DATA_DIR=/opt/trustops-data`). You do not need to
back them up separately unless you maintain custom overlays in the lake.

## Helm / Kubernetes Backup

The chart mounts a PVC at `lake.mountPath` (default `/lake`):

```yaml
# deploy/helm/trustops/values.yaml
lake:
  persistence:
    enabled: true
    size: 20Gi
    accessMode: ReadWriteOnce
  mountPath: /lake
```

PVC name: `{release}-lake` (e.g. `trustops-lake` when release is `trustops`).

### 1. Quiesce Writes (recommended)

Scale the deployment to zero and wait for the scheduler CronJob to finish:

```bash
NS=trustops
RELEASE=trustops

kubectl -n "$NS" scale deployment/"$RELEASE" --replicas=0
kubectl -n "$NS" wait --for=condition=complete job -l job-name --timeout=120s 2>/dev/null || true
```

For a consistent SQLite snapshot, stop the API pod before copying `server/app.db`.
Postgres deployments can use native point-in-time recovery instead.

### 2. Snapshot The PVC

**Volume snapshot (preferred on EBS/GCE/Azure Disk):**

```bash
kubectl -n "$NS" get pvc "${RELEASE}-lake"
# Create a VolumeSnapshot via your CSI driver / cloud console.
```

**File-level copy via temporary pod:**

```bash
kubectl -n "$NS" run lake-backup --rm -it --restart=Never \
  --image=busybox:1.36 \
  --overrides='{
    "spec": {
      "containers": [{
        "name": "backup",
        "image": "busybox:1.36",
        "command": ["tar", "czf", "/backup/lake.tar.gz", "-C", "/lake", "."],
        "volumeMounts": [
          {"name": "lake", "mountPath": "/lake", "readOnly": true},
          {"name": "out", "mountPath": "/backup"}
        ]
      }],
      "volumes": [
        {"name": "lake", "persistentVolumeClaim": {"claimName": "'"${RELEASE}"'-lake"}},
        {"name": "out", "emptyDir": {}}
      ]
    }
  }'
kubectl -n "$NS" cp lake-backup:/backup/lake.tar.gz "./trustops-lake-$(date +%F).tar.gz"
```

### 3. Back Up Postgres (when configured)

If Helm values set `TRUSTOPS_DATABASE_URL` to Postgres, back up that database
with your standard tooling (`pg_dump`, managed snapshots, WAL archiving). The
lake PVC does **not** contain Postgres rows.

Example Helm env:

```yaml
env:
  - name: TRUSTOPS_DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: trustops-database
        key: url
```

## Local / Docker Backup

```bash
LAKE="${TRUSTOPS_LAKE:-build/lakehouse}"
tar czf "trustops-lake-$(date +%F).tar.gz" -C "$LAKE" .
```

Docker bind mount:

```bash
docker run --rm -v trustops-lake:/lake -v "$PWD":/backup busybox \
  tar czf /backup/lake-backup.tar.gz -C /lake .
```

Verify integrity hashes after restore:

```bash
curl -s "$TRUSTOPS_URL/api/v1/snapshots/integrity" | jq .
curl -s "$TRUSTOPS_URL/api/v1/tracking/integrity" | jq .
```

## Restore Procedure

### 1. Restore Lake Files

**Helm — replace PVC contents:**

```bash
NS=trustops
RELEASE=trustops
BACKUP=trustops-lake-2026-07-03.tar.gz

kubectl -n "$NS" scale deployment/"$RELEASE" --replicas=0
kubectl -n "$NS" scale cronjob/"$RELEASE"-scheduler --suspend=true

kubectl -n "$NS" run lake-restore --rm -it --restart=Never \
  --image=busybox:1.36 -- sh -c '
    tar xzf /backup/lake.tar.gz -C /lake
  ' \
  --overrides='...'  # mount PVC at /lake and backup file at /backup/lake.tar.gz
```

**Local:**

```bash
LAKE="${TRUSTOPS_LAKE:-build/lakehouse}"
rm -rf "$LAKE"
mkdir -p "$LAKE"
tar xzf trustops-lake-2026-07-03.tar.gz -C "$LAKE"
```

Confirm key artifacts exist:

```bash
ls "$LAKE/gold/current_posture.json"
ls "$LAKE/gold/connector_runs.jsonl"
ls "$LAKE/server/app.db"    # when using default SQLite
```

### 2. Restore Application-State DB

**SQLite (default):** restored automatically when `server/app.db` is inside the
lake tarball.

**Postgres:** restore from your `pg_dump` or snapshot into the DSN referenced by
`TRUSTOPS_DATABASE_URL`.

### 3. Migrate Schema

After any restore, run Alembic to the current revision:

```bash
security-lakehouse db upgrade --lake "$LAKE"
security-lakehouse db current --lake "$LAKE"
```

In Kubernetes:

```bash
kubectl -n "$NS" run db-upgrade --rm -it --restart=Never \
  --image=ghcr.io/msaad00/trustops:latest \
  --env="TRUSTOPS_LAKE=/lake" \
  -- security-lakehouse db upgrade --lake /lake
```

### 4. Bring Traffic Back

```bash
kubectl -n "$NS" scale cronjob/"$RELEASE"-scheduler --suspend=false
kubectl -n "$NS" scale deployment/"$RELEASE" --replicas=1
kubectl -n "$NS" rollout status deployment/"$RELEASE"
curl -fsS "$TRUSTOPS_URL/api/healthz"
```

### 5. Post-Restore Validation

Run the checks from [Release Readiness](../RELEASE_READINESS.md):

- `GET /api/healthz` over HTTPS
- Browser or API-key login
- `GET /api/v1/ingestion/status` — enabled connectors show recent syncs
- `GET /api/v1/posture/current` — score and violations load
- One connector run in `gold/connector_runs.jsonl` with `result=ok`
- Scheduler CronJob `{release}-scheduler` completes successfully
- Snapshot and tracking integrity endpoints return ok

## Restore Drill Checklist

Schedule at least quarterly:

- [ ] Restore lake tarball to a staging namespace or laptop path
- [ ] Run `security-lakehouse db upgrade --lake <path>`
- [ ] Confirm `gold/connector_runs.jsonl` and `current_posture.json` readable
- [ ] Issue a test API key and call `/api/v1/posture/current`
- [ ] Trigger one connector sync and confirm a new run row
- [ ] Document RTO/RPO actually observed

## Retention Notes

- `gold/connector_runs.jsonl` is append-only; backups grow with sync frequency.
  Archive old tarballs to object storage with encryption and lifecycle rules.
- Assessment snapshots under `gold/snapshots/` are hash-chained; do not edit
  individual files during restore — replace the whole lake prefix.
- API keys are stored hashed; you cannot recover plaintext tokens from backup.
  Re-issue keys after a compromise restore.

## Related Docs

- [Shareable POC Hosting](../SHAREABLE_POC_HOSTING.md) — PVC and scheduler defaults
- [Deploy README](../../deploy/README.md) — Helm value groups
- [Continuous Ingestion](../CONTINUOUS_INGESTION.md) — connector run contract
- [Release Readiness](../RELEASE_READINESS.md) — post-restore gate
