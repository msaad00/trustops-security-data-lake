"use client";

import { ClipboardCopy, Terminal } from "lucide-react";
import { KodaLogo } from "@/components/brand/TrustOpsLogo";
import { KodaMark } from "@/components/brand/KodaMark";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { BRAND } from "@/lib/brand";
import { notify } from "@/lib/toast";

const MCP_TOOLS = [
  "get_posture",
  "list_controls",
  "list_evidence",
  "list_violations",
  "get_audit_readiness",
  "create_agent_run",
  "approve_agent_decision",
  "create_snapshot",
  "run_workflow",
] as const;

const CURSOR_CONFIG = `{
  "mcpServers": {
    "trustops": {
      "command": "trustops-mcp",
      "env": {
        "TRUSTOPS_API_URL": "http://127.0.0.1:8787",
        "TRUSTOPS_API_KEY": "tops_..."
      }
    }
  }
}`;

export function McpSetupStrip() {
  const copy = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      notify.success(`${label} copied`);
    } catch {
      notify.error("Clipboard unavailable");
    }
  };

  return (
    <section className="grid gap-4 rounded-2xl border border-line bg-white p-4 shadow-sm sm:p-5">
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-4">
        <KodaLogo markSize="lg" subtitle="MCP Server" />
        <Badge tone="info">stdio · {MCP_TOOLS.length}+ tools</Badge>
      </div>
      <p className="max-w-3xl text-sm leading-6 text-muted">
        Connect {BRAND.name} to Cursor, Claude Desktop, or any MCP host. Each
        tool advertises the {BRAND.name} mark in clients that support MCP icons
        — the same headless surface as this console and{" "}
        <code className="text-ink">/api/v1</code>.
      </p>
      <div className="grid gap-3 lg:grid-cols-2">
        <div className="grid gap-2 rounded-xl border border-line bg-slate-50 p-3">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-black uppercase tracking-wide text-muted">
              Install
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() =>
                copy(
                  "pip install 'trustops-security-data-lake[mcp]'",
                  "Install command",
                )
              }
            >
              <ClipboardCopy className="h-3.5 w-3.5" />
              Copy
            </Button>
          </div>
          <pre className="overflow-x-auto rounded-lg bg-[#07111e] p-3 text-xs text-slate-100">
            pip install &apos;trustops-security-data-lake[mcp]&apos;
          </pre>
        </div>
        <div className="grid gap-2 rounded-xl border border-line bg-slate-50 p-3">
          <div className="flex items-center justify-between gap-2">
            <span className="inline-flex items-center gap-1.5 text-xs font-black uppercase tracking-wide text-muted">
              <Terminal className="h-3.5 w-3.5" />
              Cursor / MCP host
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => copy(CURSOR_CONFIG, "MCP config")}
            >
              <ClipboardCopy className="h-3.5 w-3.5" />
              Copy
            </Button>
          </div>
          <pre className="max-h-36 overflow-auto rounded-lg bg-[#07111e] p-3 text-xs text-slate-100">
            {CURSOR_CONFIG}
          </pre>
        </div>
      </div>
      <div className="flex min-w-0 flex-wrap gap-2">
        {MCP_TOOLS.map((tool) => (
          <span
            key={tool}
            className="inline-flex items-center gap-1.5 rounded-full border border-line bg-panel px-2.5 py-1 text-[11px] font-bold text-ink"
          >
            <KodaMark size="xs" gradientId={`koda-mcp-tool-${tool}`} />
            {tool}
          </span>
        ))}
      </div>
      <p className="text-xs text-muted">
        Example config:{" "}
        <code className="text-ink">.cursor/mcp.json.example</code> in the repo.
        Set <code className="text-ink">TRUSTOPS_PUBLIC_URL</code> on hosted
        servers so remote MCP clients fetch the logo from{" "}
        <code className="text-ink">/brand/trustops-mark.svg</code>.
      </p>
    </section>
  );
}
