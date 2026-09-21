Automated framework sync detected drift in `frameworks/registry.json`.
Reviewer should verify each updated `source_sha256` against the
regulator's site before merging.

```
{
  "count": 15,
  "results": [
    {
      "framework_id": "soc2",
      "new_sha": "2ede772c1906bd800641ddd37224c6df1fdb767769b9bc677408f803aaa8ce83",
      "old_sha": null,
      "pulled_at": "2026-09-21T12:48:49.734962Z",
      "reason": null,
      "state": "updated"
    },
    {
      "framework_id": "nist-ai-rmf",
      "new_sha": "d04de1ce96f93a5a40fad29aa6475de93d7d6117c3e8d117b18da8c75863a3e6",
      "old_sha": null,
      "pulled_at": "2026-09-21T12:48:49.871259Z",
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
      "new_sha": "d0cc4088f6786bd4f900dba51a45a1f1600cf2a5e28343850b764f6dc31621ef",
      "old_sha": null,
      "pulled_at": "2026-09-21T12:48:50.324319Z",
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
      "new_sha": "893cebbf2cf8c22a1076970dd083f88a28f67d3c77726988672763498e9819f2",
      "old_sha": null,
      "pulled_at": "2026-09-21T12:48:50.869653Z",
      "reason": null,
      "state": "updated"
    },
    {
      "framework_id": "gdpr-2016-679",
      "new_sha": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "old_sha": null,
      "pulled_at": "2026-09-21T12:48:51.066783Z",
      "reason": null,
      "state": "updated"
    },
    {
      "framework_id": "eu-ai-act-2024-1689",
      "new_sha": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "old_sha": null,
      "pulled_at": "2026-09-21T12:48:51.236255Z",
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
      "new_sha": "14c85cf90b56b825f70507cbf1827d83bd4dad5e1b8bcadfdf977ac3f43f1230",
      "old_sha": null,
      "pulled_at": "2026-09-21T12:48:51.998845Z",
      "reason": null,
      "state": "updated"
    },
    {
      "framework_id": "nist-csf-2.0",
      "new_sha": "1bad48c0f7566fb1532476438f3126fbf9d15f3f5675387bba209ed1a57b0bed",
      "old_sha": null,
      "pulled_at": "2026-09-21T12:48:52.104847Z",
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
      "new_sha": "7261a516a0fbf8bda5c0278ba000f07acf94f1db66b0f21793b4a391e6db80c2",
      "old_sha": null,
      "pulled_at": "2026-09-21T12:48:52.488336Z",
      "reason": null,
      "state": "updated"
    }
  ]
}
```
