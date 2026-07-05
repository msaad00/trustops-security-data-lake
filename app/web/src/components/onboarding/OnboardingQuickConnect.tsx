"use client";

import Link from "next/link";
import { ConnectorMark } from "@/components/connectors/ConnectorMark";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const QUICK_CONNECT = [
  {
    id: "aws-posture",
    label: "AWS",
    detail: "Cross-account read-only posture role",
  },
  {
    id: "azure-posture",
    label: "Azure",
    detail: "Subscription Reader or federated identity",
  },
  {
    id: "gcp-posture",
    label: "Google Cloud",
    detail: "Project IAM via ADC or WIF",
  },
  {
    id: "snowflake-evidence-lake",
    label: "Snowflake",
    detail: "Governed evidence views in your account",
  },
  {
    id: "github-security",
    label: "GitHub",
    detail: "Repo governance and security signals",
  },
  {
    id: "gitlab-security",
    label: "GitLab",
    detail: "Project governance sync",
  },
] as const;

export function OnboardingQuickConnect() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Quick connect</CardTitle>
        <CardDescription>
          Deep-link into probe → discover → test → enable → sync for each
          source.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-2 sm:grid-cols-2">
        {QUICK_CONNECT.map(({ id, label, detail }) => (
          <Link
            key={id}
            href={`/connectors/?connect=${id}`}
            className="flex items-center gap-3 rounded-xl border border-line bg-slate-50 p-3 transition hover:border-brand hover:bg-white"
          >
            <ConnectorMark connectorId={id} name={label} size="sm" />
            <div className="min-w-0">
              <div className="font-black text-ink">{label}</div>
              <div className="truncate text-xs text-muted">{detail}</div>
            </div>
          </Link>
        ))}
      </CardContent>
    </Card>
  );
}
