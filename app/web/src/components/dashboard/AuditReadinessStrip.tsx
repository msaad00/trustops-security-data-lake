"use client";

import Link from "next/link";
import { ArrowRight, ClipboardCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { useAuditReadiness } from "@/lib/api/hooks";

export function AuditReadinessStrip() {
  const audit = useAuditReadiness();
  const data = audit.data;
  if (!data) return null;

  const tone =
    data.state === "audit_ready"
      ? "ready"
      : data.state === "on_track"
        ? "attention"
        : "critical";

  return (
    <Card className="border-line bg-surface p-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <ClipboardCheck className="h-5 w-5 text-brand" />
          <div>
            <div className="text-xs font-black uppercase tracking-wider text-muted">
              Audit room
            </div>
            <div className="text-sm font-bold text-ink">
              {data.audit_score}% audit score · {data.control_tests.passing}/
              {data.control_tests.total} tests passing
            </div>
          </div>
          <Badge tone={tone}>{data.state.replace(/_/g, " ")}</Badge>
          {data.gaps.length > 0 && (
            <span className="text-xs text-muted">
              {data.gaps.length} gap{data.gaps.length === 1 ? "" : "s"} to close
            </span>
          )}
        </div>
        <Link
          href="/audit-room"
          className="inline-flex items-center gap-1 text-sm font-extrabold text-brand hover:underline"
        >
          Open audit room
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </Card>
  );
}
