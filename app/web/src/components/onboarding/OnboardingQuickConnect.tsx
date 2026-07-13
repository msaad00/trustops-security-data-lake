"use client";

import Link from "next/link";
import { ConnectorMark } from "@/components/connectors/ConnectorMark";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const QUICK_CONNECT = [
  { id: "aws-posture", label: "AWS" },
  { id: "azure-posture", label: "Azure" },
  { id: "gcp-posture", label: "Google Cloud" },
  { id: "snowflake-evidence-lake", label: "Snowflake" },
  { id: "github-security", label: "GitHub" },
  { id: "gitlab-security", label: "GitLab" },
] as const;

export function OnboardingQuickConnect() {
  return (
    <Card>
      <CardHeader className="p-3 pb-2">
        <CardTitle className="ui-section-title">Quick connect</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-1.5 p-3 pt-0 sm:grid-cols-2">
        {QUICK_CONNECT.map(({ id, label }) => (
          <Link
            key={id}
            href={`/connectors/?connect=${id}&onboarding=1`}
            className="flex items-center gap-2 rounded-md border border-line bg-surface-muted px-2.5 py-2 transition hover:border-brand"
          >
            <ConnectorMark connectorId={id} name={label} size="sm" />
            <span className="text-sm font-medium text-ink">{label}</span>
          </Link>
        ))}
      </CardContent>
    </Card>
  );
}
