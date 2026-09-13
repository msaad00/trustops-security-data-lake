# Collection completeness

A connector sync must finish every required read before publishing evidence or advancing its watermark. An error leaves the prior raw evidence, assessment and watermark available; the run is recorded as an error so the operator can retry after correcting the source problem.

The shared cursor iterator raises `IncompleteCollectionError` if another page remains when its page budget is reached. Its `cursor` attribute supports explicit resumption by the caller. Provider cursors are excluded from the exception text and persisted run errors. A caller that consumes only part of the iterator has not established completion.

GCP posture collection requires successful IAM, organization-policy and asset-inventory reads. A missing organization-policy client, disabled API, denied permission or failed page read fails collection. A successful empty response remains valid. Configure Application Default Credentials with read access to the requested project and install the required Google Cloud clients; retry after resolving access or API availability. No extra write permissions are required.

These checks establish completion of the configured reads. They do not establish that the selected project scope includes every account, resource type or organization the operator intended to assess.
