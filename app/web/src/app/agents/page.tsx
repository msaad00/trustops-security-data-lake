"use client";

import { useMemo, useState } from "react";
import { Bot, ClipboardCopy, Loader2, Play } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { notify } from "@/lib/toast";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PageHeader } from "@/components/PageHeader";
import { useAuditorMode } from "@/lib/state/auditor";

interface RouteSpec {
  method: "GET" | "POST";
  path: string;
  description: string;
  scope:
    | "posture"
    | "controls"
    | "evidence"
    | "assets"
    | "snapshots"
    | "workflows"
    | "trust"
    | "audit"
    | "graph";
  body_example?: Record<string, unknown>;
  path_params?: Array<{ name: string; placeholder: string }>;
}

const ROUTES: RouteSpec[] = [
  {
    method: "GET",
    path: "/api/v1/healthz",
    description: "Server liveness envelope.",
    scope: "posture",
  },
  {
    method: "GET",
    path: "/api/v1/posture/current",
    description: "Full assessment posture + violations + frameworks.",
    scope: "posture",
  },
  {
    method: "GET",
    path: "/api/v1/control-tests?result=fail&limit=10",
    description: "Paginated control test results with confidence + freshness.",
    scope: "controls",
  },
  {
    method: "GET",
    path: "/api/v1/controls?sort=-risk_score",
    description: "Sortable control posture catalog.",
    scope: "controls",
  },
  {
    method: "GET",
    path: "/api/v1/violations?severity=critical,high",
    description: "Filterable open control failures.",
    scope: "controls",
  },
  {
    method: "GET",
    path: "/api/v1/evidence?control_ids=SOC2-CC6.1",
    description: "Filterable silver normalized events.",
    scope: "evidence",
  },
  {
    method: "GET",
    path: "/api/v1/assets?sort=-risk_score",
    description: "Sortable asset risk roll-up.",
    scope: "assets",
  },
  {
    method: "GET",
    path: "/api/v1/snapshots",
    description: "Point-in-time snapshot list.",
    scope: "snapshots",
  },
  {
    method: "POST",
    path: "/api/v1/snapshots",
    description: "Freeze a snapshot.",
    scope: "snapshots",
    body_example: { reason: "audit_request" },
  },
  {
    method: "GET",
    path: "/api/connectors",
    description: "Connector registry joined with state + last probe.",
    scope: "controls",
  },
  {
    method: "POST",
    path: "/api/connectors/{id}/probe",
    description: "Run a probe against a connector.",
    scope: "controls",
    path_params: [{ name: "id", placeholder: "github-security" }],
    body_example: {},
  },
  {
    method: "GET",
    path: "/api/frameworks",
    description: "Framework registry + provenance + coverage.",
    scope: "controls",
  },
  {
    method: "GET",
    path: "/api/workflows",
    description: "Workflow list (latest version per id).",
    scope: "workflows",
  },
  {
    method: "GET",
    path: "/api/workflows/actions",
    description: "Action library with input/output schemas.",
    scope: "workflows",
  },
  {
    method: "POST",
    path: "/api/workflows/actions/run",
    description: "Execute a single action against the lake.",
    scope: "workflows",
    body_example: {
      node_type: "check.evidence_exists",
      params: { control_id: "SOC2-CC6.1", minimum: 1 },
    },
  },
  {
    method: "GET",
    path: "/api/trust-shares",
    description: "List active trust-share tokens.",
    scope: "trust",
  },
  {
    method: "POST",
    path: "/api/trust-shares",
    description: "Issue a new auditor share (returns raw token once).",
    scope: "trust",
    body_example: {
      role: "auditor",
      scope: "posture_full",
      expires_in_hours: 24,
    },
  },
  {
    method: "GET",
    path: "/api/audit-log",
    description: "Unified activity stream across every append-only log.",
    scope: "audit",
  },
  {
    method: "GET",
    path: "/api/graph",
    description: "Framework → control → evidence → asset graph.",
    scope: "graph",
  },
  {
    method: "GET",
    path: "/api/crosswalk",
    description: "Framework × framework cross-mapping matrix.",
    scope: "graph",
  },
];

const SCOPE_TONE: Record<
  RouteSpec["scope"],
  "ready" | "info" | "attention" | "critical" | "default"
> = {
  posture: "info",
  controls: "ready",
  evidence: "info",
  assets: "attention",
  snapshots: "critical",
  workflows: "ready",
  trust: "critical",
  audit: "default",
  graph: "info",
};

function expandPath(route: RouteSpec, params: Record<string, string>): string {
  let path = route.path;
  for (const p of route.path_params ?? []) {
    const value = params[p.name] || p.placeholder;
    path = path.replace(`{${p.name}}`, encodeURIComponent(value));
  }
  return path;
}

function curlFor(
  route: RouteSpec,
  path: string,
  body: string,
  role: string,
): string {
  const lines: string[] = [`curl -s -X ${route.method} \\`];
  if (role) lines.push(`  -H 'X-Trust-Role: ${role}' \\`);
  if (route.method === "POST") {
    lines.push(`  -H 'content-type: application/json' \\`);
    lines.push(`  -d '${body || "{}"}' \\`);
  }
  lines.push(`  http://127.0.0.1:8787${path}`);
  return lines.join("\n");
}

export default function AgentsPage() {
  const auditor = useAuditorMode();
  const [selected, setSelected] = useState<RouteSpec>(ROUTES[1]);
  const [pathParams, setPathParams] = useState<Record<string, string>>({});
  const [body, setBody] = useState("");
  const [role, setRole] = useState(auditor ? "auditor" : "");
  const [response, setResponse] = useState<string | null>(null);
  const [status, setStatus] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);

  const flash = (msg: string) => notify.message(msg);

  const path = useMemo(
    () => expandPath(selected, pathParams),
    [selected, pathParams],
  );
  const curl = useMemo(
    () => curlFor(selected, path, body, role),
    [selected, path, body, role],
  );

  const execute = async () => {
    setBusy(true);
    setResponse(null);
    setStatus(null);
    try {
      const init: RequestInit = {
        method: selected.method,
        headers: {
          ...(role ? { "X-Trust-Role": role } : {}),
          ...(selected.method === "POST"
            ? { "content-type": "application/json" }
            : {}),
        },
      };
      if (selected.method === "POST") init.body = body || "{}";
      const res = await fetch(path, init);
      setStatus(res.status);
      const text = await res.text();
      try {
        setResponse(JSON.stringify(JSON.parse(text), null, 2));
      } catch {
        setResponse(text);
      }
    } catch (err) {
      setResponse(String((err as Error).message));
    } finally {
      setBusy(false);
    }
  };

  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      flash("Copied.");
    } catch {
      flash("Clipboard unavailable.");
    }
  };

  const selectRoute = (route: RouteSpec) => {
    setSelected(route);
    setPathParams({});
    setBody(
      route.body_example ? JSON.stringify(route.body_example, null, 2) : "",
    );
    setResponse(null);
    setStatus(null);
  };

  return (
    <div className="grid min-w-0 gap-5 px-4 py-5 sm:px-5 lg:px-7">
      <PageHeader
        eyebrow="Agent API"
        title="Live try-it console"
        description="Every JSON contract the workbench calls. Pick a route, fill params, hit Run. The same shapes serve agents and humans — X-Trust-Role: auditor returns 403 on POSTs and redacts owners/notes on GETs."
        actions={
          <Badge tone="info">
            <Bot className="mr-1 h-3 w-3" /> {ROUTES.length} routes
          </Badge>
        }
      />

      <div className="grid gap-5 lg:grid-cols-[320px_minmax(0,1fr)]">
        <Card className="overflow-hidden">
          <CardHeader>
            <CardTitle>Routes</CardTitle>
            <CardDescription>Click to load into the runner.</CardDescription>
          </CardHeader>
          <div className="grid gap-1 p-4 pt-0">
            {ROUTES.map((route) => (
              <button
                key={route.method + route.path}
                type="button"
                onClick={() => selectRoute(route)}
                className={[
                  "grid grid-cols-[auto_minmax(0,1fr)] items-center gap-2 rounded-lg px-2 py-1.5 text-left text-xs",
                  selected.method + selected.path === route.method + route.path
                    ? "bg-ink text-white"
                    : "text-slate-700 hover:bg-slate-50",
                ].join(" ")}
              >
                <Badge tone={route.method === "POST" ? "critical" : "ready"}>
                  {route.method}
                </Badge>
                <code className="truncate">{route.path}</code>
              </button>
            ))}
          </div>
        </Card>

        <div className="grid gap-5">
          <Card className="overflow-hidden">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Badge tone={selected.method === "POST" ? "critical" : "ready"}>
                  {selected.method}
                </Badge>
                <code className="text-sm text-ink">{selected.path}</code>
                <Badge tone={SCOPE_TONE[selected.scope]}>
                  {selected.scope}
                </Badge>
              </CardTitle>
              <CardDescription>{selected.description}</CardDescription>
            </CardHeader>
            <div className="grid gap-3 p-5 pt-0">
              {(selected.path_params ?? []).map((p) => (
                <label
                  key={p.name}
                  className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted"
                >
                  {p.name}
                  <input
                    value={pathParams[p.name] ?? ""}
                    placeholder={p.placeholder}
                    onChange={(e) =>
                      setPathParams((prev) => ({
                        ...prev,
                        [p.name]: e.target.value,
                      }))
                    }
                    className="rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-brand"
                  />
                </label>
              ))}
              <label className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted">
                X-Trust-Role (optional)
                <input
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  placeholder="auditor (leave blank for default)"
                  className="rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-brand"
                />
              </label>
              {selected.method === "POST" && (
                <label className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted">
                  Body (JSON)
                  <textarea
                    rows={6}
                    value={body}
                    onChange={(e) => setBody(e.target.value)}
                    className="rounded-lg border border-line bg-white px-3 py-2 font-mono text-xs text-ink focus:outline-none focus:ring-1 focus:ring-brand"
                  />
                </label>
              )}
              <div className="flex flex-wrap items-center gap-2">
                <Button variant="primary" onClick={execute} disabled={busy}>
                  {busy ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Play className="h-4 w-4" />
                  )}{" "}
                  Run
                </Button>
                <Button variant="default" onClick={() => copy(curl)}>
                  <ClipboardCopy className="h-4 w-4" /> Copy curl
                </Button>
              </div>
            </div>
          </Card>

          <Card className="overflow-hidden">
            <CardHeader>
              <CardTitle>curl</CardTitle>
              <CardDescription>
                Reproduce this call from any shell.
              </CardDescription>
            </CardHeader>
            <pre className="overflow-auto bg-slate-950 p-4 text-xs text-slate-100">
              {curl}
            </pre>
          </Card>

          <Card className="overflow-hidden">
            <CardHeader>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <CardTitle>Response</CardTitle>
                {status !== null && (
                  <Badge
                    tone={
                      status < 300
                        ? "ready"
                        : status < 500
                          ? "attention"
                          : "critical"
                    }
                  >
                    {status}
                  </Badge>
                )}
              </div>
              <CardDescription>
                Response body is identical to what an agent would see hitting
                the same endpoint.
              </CardDescription>
            </CardHeader>
            <pre className="max-h-[420px] overflow-auto bg-slate-50 p-4 text-xs text-ink">
              {response ?? "Click Run to fire the request."}
            </pre>
          </Card>
        </div>
      </div>
    </div>
  );
}
