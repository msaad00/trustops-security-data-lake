Automated framework sync detected drift in `frameworks/registry.json`.
Reviewer should verify each updated `source_sha256` against the
regulator's site before merging.

```
{
  "count": 15,
  "results": [
    {
      "framework_id": "soc2",
      "new_sha": "1d35e56e61eac45131f5e85d22a9bce17aff1d7346b0e6820b002af41f5ad2bb",
      "old_sha": null,
      "pulled_at": "2026-09-14T12:47:49.102343Z",
      "reason": null,
      "state": "updated"
    },
    {
      "framework_id": "nist-ai-rmf",
      "new_sha": "1a44a579164c61d3d96e46000efc95d6a274365103714886dd4488aa2522159b",
      "old_sha": null,
      "pulled_at": "2026-09-14T12:47:49.213142Z",
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
      "new_sha": "abbbde0628daa6589aad977160743e841767d22e92a73d8fafeb25625ad2c3f4",
      "old_sha": null,
      "pulled_at": "2026-09-14T12:47:49.870412Z",
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
      "new_sha": "b2cf211141e0640adb38d6b6387af932595c9f5825cc3166dbe1701e24a94a79",
      "old_sha": null,
      "pulled_at": "2026-09-14T12:47:50.787352Z",
      "reason": null,
      "state": "updated"
    },
    {
      "framework_id": "gdpr-2016-679",
      "new_sha": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "old_sha": null,
      "pulled_at": "2026-09-14T12:47:51.030533Z",
      "reason": null,
      "state": "updated"
    },
    {
      "framework_id": "eu-ai-act-2024-1689",
      "new_sha": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "old_sha": null,
      "pulled_at": "2026-09-14T12:47:52.716447Z",
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
      "new_sha": "e5c622f94fa1a195730fe0b0d81d19541097bb876be793572abffec8205448fa",
      "old_sha": null,
      "pulled_at": "2026-09-14T12:47:53.020207Z",
      "reason": null,
      "state": "updated"
    },
    {
      "framework_id": "nist-csf-2.0",
      "new_sha": "8a786d901d30c3ae9c2bdf078d79093bee90a53a902d2343949b81af36575d05",
      "old_sha": null,
      "pulled_at": "2026-09-14T12:47:53.075013Z",
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
      "new_sha": "6ccd70a17b00a1bf2f98a760627068295bbc22acb5a4be5a43e4182538e06c76",
      "old_sha": null,
      "pulled_at": "2026-09-14T12:47:53.516995Z",
      "reason": null,
      "state": "updated"
    }
  ]
}
```
