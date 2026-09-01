# Changelog

All notable TrustOps changes are summarized here. Versions follow semver for the
Python package, Helm chart, and bundled web console.

## Unreleased

Release theme: **secure dependencies + clearer first-run story**. Restores the
release security gate and makes the README's product journey readable at a
glance without changing TrustOps proof semantics.

### Security

- Raised the optional Snowflake connector floor to 4.7.1 and regenerated the
  lockfile, replacing 4.6.0 after `pip-audit` identified CVE-2026-15925.

### Added

- Common Control Framework safeguards for controlled maintenance and
  separation of duties, sourced from the NIST SP 800-171 Rev. 2 crosswalk.
  Their new mappings remain proposed pending human review.

### Changed

- Rebuilt the README identity system around a crisp scalable hero, transparent
  wordmark, simpler four-stage operating-loop banner, and clearer navigation.
- Consolidated the queued Python and web dependency updates into one verified
  lockfile refresh.

## 0.2.6 - 2026-08-17

Release theme: **maintenance + unattended Google Workspace sync**. Closes the
last gap left by the 0.2.4 OAuth refresh work and refreshes dependencies.

### Added

- Google Workspace can be enabled with refresh-token material alone
  (`refresh_token_ref` + `client_id` + `client_secret_ref`) instead of a
  pre-minted access token. The runner already minted tokens from that triple;
  enablement validation and the console connector form previously demanded a
  static `credential_ref` anyway, so unattended sync could not be configured
  through the console. A partially-supplied triple is now rejected by name at
  probe and enable time rather than silently falling back to the static-token
  path.

### Changed

- Web console dependencies updated: `next` and `eslint-config-next` 16.3.0 ->
  16.3.1, `@xyflow/react` 12.11.2 -> 12.11.3, `@dagrejs/dagre` 3.1.0 -> 3.1.1,
  `caniuse-lite` -> 1.0.30001809, `postcss` -> 8.5.26. The console still builds
  with the pinned Webpack builder.
- Release workflow actions updated to their current majors:
  `docker/login-action` v4, `docker/metadata-action` v6,
  `softprops/action-gh-release` v3.
- The example MCP host config moved from `.cursor/mcp.json.example` to
  `examples/mcp/mcp.json.example`; it is a generic stdio MCP config, not
  editor-specific. Contents are unchanged.
- `ROADMAP.md` P7 no longer presents its issue table as open work; all nine
  linked issues are closed on GitHub, and `docs/PRODUCT_SHAPE.md` carries the
  honest per-item status (two are still _Partial_).

## 0.2.5 - 2026-08-14

Release theme: **complete the connector-resilience pass**. Closes the last gap
from the resilience audit — the append-mode readers that pulled a whole window
in one request now paginate it.

### Fixed

- ClickHouse, SIEM, and runtime-gateway readers paginate their `since`-window
  instead of truncating it at the server's first page. ClickHouse keyset-paginates
  on the composite `(event_time, event_id)` cursor with `LIMIT`, so rows sharing an
  `event_time` across a page boundary are never dropped and the loop always
  terminates. SIEM and runtime-gateway follow an optional `next_cursor` envelope
  via `?cursor=`; an export that returns a bare list is still read as a single
  page, so a non-paginating endpoint keeps working unchanged.

## 0.2.4 - 2026-08-14

Release theme: **honest framework coverage + connector resilience**. Separates
the coverage a compliance product may attest to from the coverage it merely
touches, and hardens the read-only connectors against redirects and rate limits.

### Security

- Repo-governance connector (GitHub/GitLab) now reaches its APIs through the
  same SSRF guard as every other HTTP connector, re-validating each redirect hop
  and stripping `Authorization` across origins. The GitLab base URL is
  operator-configurable, so a redirect could otherwise pivot the request and its
  bearer token at an internal address.

### Added

- Framework coverage matrix that splits **evaluatable** (any safeguard mapping)
  from **attestable** (human-reviewed — the only coverage an auditor accepts),
  surfaced via `frameworks coverage`, an MCP tool, and a committed, gated doc.
- Mapping review-queue (`frameworks review-queue`, `--framework` to scope, plus
  an MCP tool) that lists the proposed safeguard→requirement mappings awaiting
  expert sign-off, each paired with the reviewed anchors on the same safeguard.
  It never auto-promotes a mapping — accepting one stays a domain-expert call.
- Google Workspace connector supports OAuth refresh tokens for unattended sync,
  exchanging the refresh token when the access token is missing, near expiry, or
  rejected once with 401. The refresh token and client secret resolve file-first,
  and the resolved access token is held in memory only, never persisted.

### Fixed

- Connectors retry transient rate-limit / gateway errors (429/5xx, honoring
  `Retry-After`, with exponential backoff + jitter) instead of failing a whole
  sync on a single blip: SIEM, runtime-gateway, ClickHouse, and repo-governance.
  4xx stays terminal.
- Google Workspace connector follows the Directory API `nextPageToken` instead
  of a single request, so a tenant with more than a page of users/groups/members
  is no longer silently truncated.

## 0.2.3 - 2026-08-13

Release theme: **security + supply-chain currency**. Publishes the fixes and the
new connector work that landed on `main` after 0.2.2.

### Security

- Upgraded the bundled web console to Next.js 16, clearing four high-severity
  production advisories (nanoid, postcss, sharp, and the transitive next chain).
- AWS connector: `password_policy`/`console_access` now surface unexpected IAM
  errors instead of swallowing them into a false control pass.
- `required_post_scope` fails closed — a mutating route not explicitly scoped is
  denied rather than accepting the low `write` scope.

### Added

- AWS connector cloud-linking: read-only posture role, a dedicated connector
  runtime role, and the cloud-link console flow.

### Fixed

- Dropped the opaque `/api/{rest}` catch-all from the published OpenAPI spec and
  catalogued six previously undocumented served routes.
- Helm: pin the scheduler CronJob to the API pod's node when the lake PVC is
  ReadWriteOnce, so it can mount; chart version is now gated against the release.
- Corrected the `db upgrade` command in the hosted deployment guide.

### Docs

- README status badges + PyPI classifiers; architecture diagrams now use real
  vendor logos and the official Snowflake/ClickHouse marks with proportionate
  arrowheads.

## 0.2.2 - 2026-08-12

Release theme: **audit follow-through**. Applies the confirmed findings from a
four-lane audit (code / CI / product surfaces / packaging).

### Security

- Routed the Google Workspace connector client through the shared `netguard`
  guarded opener — the one credentialed client still on raw `urllib` after the
  0.2.1 egress hardening, so its OAuth bearer can no longer follow a cross-origin
  redirect.
- Stripped local-only options (`fixture_dir`) from the connector configure
  forward-merge so a value seeded off-API cannot re-attach on a later API call.
- Constant-time trust-share token comparison.

### Fixed

- AWS access keys with an unparseable `CreateDate` no longer score a false pass
  on the rotation control.
- `__version__` is derived from installed distribution metadata (no more drift).
- Helm chart version tracks the released image tag; release verification now
  gates on it.

## 0.2.1 - 2026-08-12

Release theme: **egress SSRF hardening**. Closes three confirmed server-side
request forgery findings that shared one root cause — the outbound guards
validated only the first URL, then followed redirects (and server-supplied
pagination `Link` headers) to unvalidated hosts.

### Security

- Added `netguard.open_guarded`/`open_public`: a shared HTTP opener that re-runs
  the caller's SSRF/allowlist validator on every redirect hop and drops
  `Authorization`/`Cookie` headers on any cross-origin hop.
- Routed all host-based connector clients (Okta, SIEM, ClickHouse, runtime
  gateway, Jira) through the guarded opener, closing the connector probe/discover
  SSRF and the Okta `Link`-header token-pivot.
- Reran the workflow webhook/Slack/Jira egress path through the guarded opener so
  a 302 from an allowlisted host can no longer pivot the request (or its secret
  headers, or the response body) at an internal address.

## 0.2.0 - 2026-06-29

Release theme: **invite-only hosted POC readiness**. This release turns the repo
from a local/security-lake proof into a more coherent self-hosted TrustOps
platform: deployable by URL, usable by humans, and callable by headless agents.

### Product

- Added a first-run launch surface at `/console/poc/` that checks public URL,
  human auth, headless access, source sync, trust shares, and agent review state.
- Streamlined connector onboarding so Snowflake setup starts with identity,
  discovers granted scope, then lets the operator select read objects before
  testing/enabling.
- Added connector sync proof in the drawer so operators can see latest sync
  result, evidence count, fingerprint, and timing without opening raw logs.
- Added a governed agent harness launcher in the console with sequential vs.
  LangGraph orchestration, model toggle, budget profiles, persisted runs,
  decision review, and approval-gated writes.
- Added agent review readiness to the launch flow so the hosted POC path can go:
  connect source -> sync -> assess -> run governed review -> share trust.

### Evidence, Connectors, And Ingestion

- Proved live AWS, Azure, and Snowflake ingestion paths through the same
  scenario contract used by fixtures and CI.
- Added Snowflake read-scope discovery for warehouses, databases, schemas, and
  granted views.
- Hardened continuous ingestion docs around incremental reads, idempotency,
  retry safety, scheduler operation, and customer-owned lake boundaries.
- Added pluggable sink and lake-adapter guidance for Snowflake, ClickHouse,
  DuckDB, local files, and existing evidence-lake reads.

### Agent And Workflow Runtime

- Added persisted `agent_runs` with input hashes, budget metadata, evaluation
  results, proposed decisions, approval state, and API/MCP access.
- Added optional LangGraph orchestration while keeping the deterministic
  assessment engine model-independent and usable with zero LLM configured.
- Added model budget controls for context size, fact count, and output tokens.
- Kept writes behind RBAC, allow-listed action types, idempotency, and approval.

### Security And Operations

- Hardened API error handling and CodeQL findings around path use and exception
  exposure.
- Added API pagination/rate-limit robustness and safer connector error surfaces.
- Added hosted POC, AWS + Snowflake, live cloud, and continuous ingestion
  runbooks.
- Added OIDC/SAML/API-key server-mode docs, tenant lake boundaries, redaction,
  hashes, append-only audit records, and trust-share guidance.

### Known Gaps Before Public SaaS

- No public self-serve signup, billing, SCIM lifecycle, or multi-customer
  account marketplace.
- Connector auth is POC-capable but still needs more OAuth/service-role wizards,
  secret-manager integrations, and provider-specific hosted UX polish.
- Framework packs are seeded and source-linked, but not full certification-grade
  coverage for every framework.
- Workflow automation has a usable DAG/canvas, templates, and runs, but still
  needs deeper run inspection, retries, approvals, and action logs.
- Production operations need backup/restore drills, external secret sync,
  multi-replica guidance, alerting, WAF/API gateway guidance, and hosted
  observability before a broad public launch.
