# Agent Harness

TrustOps can run human and headless agent workflows without moving compliance
truth into an LLM.

The core remains deterministic:

```text
connectors -> evidence -> assets -> controls -> mappings -> posture -> snapshots -> trust shares -> audit
```

The optional agent harness wraps that core:

```text
redacted TrustOps facts -> deterministic tools -> optional model context -> proposed actions -> approval -> TrustOps API write -> audit event
```

## Package shape

The first harness lives under `security_lakehouse.agents`:

- `providers.py` reads optional model configuration from environment.
- `state.py` defines the shared agent run state and action proposal record.
- `tools.py` exposes typed, redaction-aware TrustOps fact readers.
- `model_contract.py` builds the model-safe prompt/context and validates
  model-proposed tool calls.
- `model_client.py` contains dependency-free optional provider clients for
  Ollama, OpenAI-compatible APIs, and Anthropic.
- `graphs.py` runs the first posture-review flow and can compile a LangGraph
  graph when `trustops-security-data-lake[agents]` is installed.

## Provider defaults

No model is required. If no provider is configured, the harness runs in
`rules_only` mode.

Environment knobs:

| Variable                         | Purpose                                                                                        |
| -------------------------------- | ---------------------------------------------------------------------------------------------- |
| `TRUSTOPS_AGENT_PROVIDER`        | `rules_only`, `ollama`, `openai`, `openai_compatible`, `anthropic`, or a future adapter        |
| `TRUSTOPS_AGENT_MODEL`           | Provider model name                                                                            |
| `TRUSTOPS_AGENT_BASE_URL`        | Local provider URL, defaulting to Ollama at `http://127.0.0.1:11434` when provider is `ollama` |
| `TRUSTOPS_AGENT_API_KEY_ENV`     | Name of the environment variable holding the provider API key                                  |
| `TRUSTOPS_AGENT_USE_MODEL`       | Set to `1` to actually call the provider; unset means deterministic harness only               |
| `TRUSTOPS_AGENT_TIMEOUT_SECONDS` | Optional provider request timeout, clamped between 1 and 120 seconds                           |

`openai_compatible` is supported for local or customer-chosen providers that
serve `/chat/completions`. The harness records provider metadata but never
prints raw API keys.

## First workflow

`run_posture_review(...)`:

1. loads current posture
2. applies role redaction
3. loads missing/stale/expired evidence gaps
4. proposes evidence-request actions
5. marks every write as `requires_approval`

This is intentionally deterministic. LangGraph can orchestrate the same nodes,
and later model-backed nodes can summarize or prioritize, but they must consume
the already-redacted state and act only through TrustOps APIs.

With `TRUSTOPS_AGENT_USE_MODEL=1`, the optional provider receives:

- the objective
- role-redacted posture
- role-redacted evidence gaps
- deterministic action proposals
- an allowed tool manifest
- a strict JSON output schema

The model may return summaries, priority ordering, and proposed tool calls.
TrustOps validates tool names and keeps every write as `requires_approval`.
The model cannot mark a control passing, mutate evidence, bypass RBAC, or
execute writes.

## Self-hosted run modes

Teams can run the harness without changing the compliance engine:

| Mode           | How it runs                                                                              | Use when                       |
| -------------- | ---------------------------------------------------------------------------------------- | ------------------------------ |
| CLI            | `security-lakehouse agents posture-review --lake <lake>`                                 | local audits, CI checks, demos |
| Scheduler      | cron, Kubernetes `CronJob`, or the TrustOps scheduler                                    | recurring evidence-gap review  |
| Service worker | internal worker calls `/api/v1/*` and writes proposed actions back through TrustOps APIs | production agent operations    |
| UI/API trigger | console button or headless API starts a saved workflow                                   | human-in-the-loop review       |

Self-hosted deployments keep the same boundaries: tenant-scoped lake path,
server-side RBAC, redacted reads, append-only audit events, and approval before
agent-proposed writes. LangGraph is useful for branching, retries, multi-agent
review, and long-running state, but it is not the source of compliance truth.

## Non-negotiables

Agents do not own:

- RBAC
- tenant isolation
- evidence freshness
- control pass/fail evaluation
- redaction policy
- idempotency
- snapshot hashes
- audit truth

Those stay in TrustOps core and tests.
