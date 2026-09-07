"use client";

import Link from "next/link";
import { useState } from "react";
import { Check, Clipboard, Database, FileJson2 } from "lucide-react";
import { Button } from "@/components/ui/button";

const NORMALIZE_COMMAND = `security-lakehouse ingestion normalize \\
  --raw ./raw/connector_events.jsonl \\
  --out ./lake`;

export function EvidencePathPanel() {
  const [copied, setCopied] = useState(false);

  async function copyCommand() {
    try {
      await navigator.clipboard.writeText(NORMALIZE_COMMAND);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  }

  return (
    <section
      aria-labelledby="evidence-path-title"
      className="grid gap-3 rounded-xl border border-line bg-panel p-3 shadow-card sm:p-4"
    >
      <div>
        <div className="ui-eyebrow">Evidence paths</div>
        <h2
          id="evidence-path-title"
          className="mt-1 text-lg font-black text-ink"
        >
          Choose an evidence path
        </h2>
        <p className="mt-1 max-w-3xl text-sm leading-5 text-muted">
          Use the same normalization and evaluation spine whether evidence is
          already in a lake or arrives through a read-only connector.
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <div className="grid gap-3 rounded-lg border border-line bg-white p-3">
          <div className="flex items-start gap-3">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-blue-50 text-brand">
              <Database className="h-4 w-4" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <h3 className="font-black text-ink">Read an existing lake</h3>
              <p className="mt-1 text-xs leading-5 text-muted">
                Connect Snowflake or ClickHouse with a read-only role. TrustOps
                reads the granted evidence surfaces and normalizes them.
              </p>
            </div>
          </div>
          <Button asChild size="sm" className="w-fit">
            <Link href="/connectors/?connect=snowflake-evidence-lake">
              Open data lake connectors
            </Link>
          </Button>
        </div>

        <div className="grid gap-3 rounded-lg border border-line bg-white p-3">
          <div className="flex items-start gap-3">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-slate-100 text-slate-700">
              <FileJson2 className="h-4 w-4" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <h3 className="font-black text-ink">
                Normalize pre-landed evidence
              </h3>
              <p className="mt-1 text-xs leading-5 text-muted">
                Put canonical raw JSONL on the server, then materialize the
                bronze, silver, and gold zones with the CLI.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 rounded-md border border-line bg-panel px-2.5 py-2">
            <code className="min-w-0 flex-1 whitespace-pre-wrap text-[11px] leading-4 text-ink">
              {NORMALIZE_COMMAND}
            </code>
            <Button
              type="button"
              size="sm"
              className="shrink-0"
              aria-label="Copy normalize command"
              onClick={copyCommand}
            >
              {copied ? (
                <Check className="h-4 w-4" aria-hidden="true" />
              ) : (
                <Clipboard className="h-4 w-4" aria-hidden="true" />
              )}
              <span className="sr-only">{copied ? "Copied" : "Copy"}</span>
            </Button>
          </div>
        </div>
      </div>

      <p className="text-xs leading-5 text-muted">
        The console never accepts local filesystem paths or raw secrets. Source
        schemas that are not canonical TrustOps raw events need an adapter
        mapping before normalization.
      </p>
    </section>
  );
}
