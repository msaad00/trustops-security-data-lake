Automated framework sync detected drift in `frameworks/registry.json`.
Reviewer should verify each updated `source_sha256` against the
regulator's site before merging.

```
{
  "count": 15,
  "results": [
    {
      "framework_id": "soc2",
      "new_sha": "0317513044233bcae0ac159d69e6cfd390e8461a5ae2c6c0256dc5e56310b20e",
      "old_sha": null,
      "pulled_at": "2026-09-07T12:37:33.162147Z",
      "reason": null,
      "state": "updated"
    },
    {
      "framework_id": "nist-ai-rmf",
      "new_sha": "f65fa0a179b3c5b744d2fff732d8947c3146987fdb48457a67b8318c0d0efba4",
      "old_sha": null,
      "pulled_at": "2026-09-07T12:37:33.261794Z",
      "reason": null,
      "state": "updated"
    },
    {
      "framework_id": "iso-27001-2022",
      "new_sha": null,
      "old_sha": null,
      "pulled_at": null,
      "reason": "fetch failed: HTTPError: HTTP Error 403: Forbidden",
      "state": "error"
    },
    {
      "framework_id": "fedramp-moderate",
      "new_sha": "24a28480f8411c0f3e5ee02156b89ade7feb0091b66cd1256184b7253b19d195",
      "old_sha": null,
      "pulled_at": "2026-09-07T12:37:33.742885Z",
      "reason": null,
      "state": "updated"
    },
    {
      "framework_id": "hipaa-security-rule",
      "new_sha": null,
      "old_sha": null,
      "pulled_at": null,
      "reason": "fetch failed: HTTPError: HTTP Error 403: Forbidden",
      "state": "error"
    },
    {
      "framework_id": "pci-dss-v4",
      "new_sha": "6bb5f0301f72d2eb8a7898490702f3d8f6f469f5bd6df73443cc66651cf82b2f",
      "old_sha": null,
      "pulled_at": "2026-09-07T12:37:34.810139Z",
      "reason": null,
      "state": "updated"
    },
    {
      "framework_id": "gdpr-2016-679",
      "new_sha": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "old_sha": null,
      "pulled_at": "2026-09-07T12:37:34.966383Z",
      "reason": null,
      "state": "updated"
    },
    {
      "framework_id": "eu-ai-act-2024-1689",
      "new_sha": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "old_sha": null,
      "pulled_at": "2026-09-07T12:37:35.005373Z",
      "reason": null,
      "state": "updated"
    },
    {
      "framework_id": "iso-42001-2023",
      "new_sha": null,
      "old_sha": null,
      "pulled_at": null,
      "reason": "fetch failed: HTTPError: HTTP Error 403: Forbidden",
      "state": "error"
    },
    {
      "framework_id": "cis_aws",
      "new_sha": "7b42e9b924146c17ba28f0a9e4bcbba5a6f52b76da50b8bc02356e4ed6a1b09e",
      "old_sha": null,
      "pulled_at": "2026-09-07T12:37:35.518493Z",
      "reason": null,
      "state": "updated"
    },
    {
      "framework_id": "nist-csf-2.0",
      "new_sha": "8811d1a95615797e27a45ea10931c57ac9b23f71cc29018729e5fdfc4ccf3cfe",
      "old_sha": null,
      "pulled_at": "2026-09-07T12:37:35.573525Z",
      "reason": null,
      "state": "updated"
    },
    {
      "framework_id": "cmmc-2-level2",
      "new_sha": null,
      "old_sha": null,
      "pulled_at": null,
      "reason": "fetch failed: HTTPError: HTTP Error 403: Forbidden",
      "state": "error"
    },
    {
      "framework_id": "iso-27017-2015",
      "new_sha": null,
      "old_sha": null,
      "pulled_at": null,
      "reason": "fetch failed: HTTPError: HTTP Error 403: Forbidden",
      "state": "error"
    },
    {
      "framework_id": "iso-27701-2019",
      "new_sha": null,
      "old_sha": null,
      "pulled_at": null,
      "reason": "fetch failed: HTTPError: HTTP Error 403: Forbidden",
      "state": "error"
    },
    {
      "framework_id": "soc1",
      "new_sha": "47fe811eef728eae84ced969f540053212e1c17b91fd5926d32a17255534f8af",
      "old_sha": null,
      "pulled_at": "2026-09-07T12:37:35.962405Z",
      "reason": null,
      "state": "updated"
    }
  ]
}
```
