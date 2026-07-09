# Adding a connector adapter (code registry)

TrustOps does not ship a runtime plugin marketplace. Connectors are **in-repo
adapters** registered in `connector_runner.REGISTRY` and
`connectors/catalog.json`.

## Quick start

```bash
security-lakehouse connectors scaffold my-vendor-evidence --title "My Vendor Evidence"
```

This writes starter files under `./connector-scaffold/` (module, test, and next
steps). Move them into the tree, implement the collector, then run:

```bash
security-lakehouse connectors validate
uv run pytest tests/test_my_vendor_evidence_connector.py
```

## Contributor checklist

1. **Collector** — `src/security_lakehouse/connectors_<slug>.py` with live +
   fixture clients and `collect_<slug>_evidence(...)`.
2. **Registry** — `_build_<slug>` builder + one line in `REGISTRY`.
3. **Catalog** — row in `connectors/catalog.json` with `is_implemented: true`.
4. **Tests** — fixture-backed sync under `tests/test_<slug>_connector.py`.
5. **Docs** — permissions and setup in `docs/CONNECTORS.md`.

## Event-log vs snapshot

| `data_shape` in catalog | Write mode | Watermark |
| ----------------------- | ---------- | --------- |
| `event_log`             | append     | yes       |
| `current_state`         | snapshot   | no        |

Append connectors receive `SyncInputs.since` from `gold/watermarks.jsonl`.

## Workflow automation

Registered connectors can be synced from workflows via `action.connector_sync`
(see `security_lakehouse/workflows.py` action catalog).

## Related docs

- [INGESTION_CONNECTORS_IDEMPOTENCY.md](INGESTION_CONNECTORS_IDEMPOTENCY.md)
- [CONNECTORS.md](CONNECTORS.md)
