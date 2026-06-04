"use client";

import { useState } from "react";
import {
  ClipboardCopy,
  Loader2,
  Share2,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PageHeader } from "@/components/PageHeader";
import {
  useCreateTrustShare,
  usePosture,
  useRevokeTrustShare,
  useTrustShares,
} from "@/lib/api/hooks";
import { useAuditorMode } from "@/lib/state/auditor";
import type { TrustShare } from "@/lib/api/types";

const HOURS_OPTIONS = [1, 4, 24, 24 * 7, 24 * 30];

export default function TrustCenterPage() {
  const auditor = useAuditorMode();
  const shares = useTrustShares();
  const createShare = useCreateTrustShare();
  const revoke = useRevokeTrustShare();
  const posture = usePosture();
  const [expiresInHours, setExpiresInHours] = useState(24);
  const [createdToken, setCreatedToken] = useState<TrustShare | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const flash = (msg: string) => {
    setToast(msg);
    window.setTimeout(() => setToast(null), 4200);
  };

  const issue = async () => {
    try {
      const { share } = await createShare.mutateAsync({
        role: "auditor",
        scope: "posture_full",
        expires_in_hours: expiresInHours,
      });
      setCreatedToken(share);
      flash(`Share issued. Copy the token now — it is never shown again.`);
    } catch (err) {
      flash(`Create share failed: ${(err as Error).message}`);
    }
  };

  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      flash("Copied to clipboard.");
    } catch {
      flash("Clipboard not available; select the text manually.");
    }
  };

  return (
    <div className="grid min-w-0 gap-5 px-4 py-5 sm:px-5 lg:px-7">
      <PageHeader
        eyebrow="Trust center"
        title="Auditor share portal"
        description="Issue scoped, expiring, revocable share tokens for external reviewers. The server stores only the hash — the raw token shows once, here, and never again. Token holders see the workbench through the auditor lens (read-only, owners and remediation notes redacted)."
        actions={
          <Badge tone="info">
            <ShieldCheck className="mr-1 h-3 w-3" />{" "}
            {posture.data?.assessment_hash?.slice(0, 12) ?? "—"}…
          </Badge>
        }
      />

      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle>Issue a new share</CardTitle>
          <CardDescription>
            Auditor role · scope <code>posture_full</code>. Token expires
            automatically; you can also revoke it below at any time.
          </CardDescription>
        </CardHeader>
        <div className="grid gap-3 p-5 pt-0 sm:grid-cols-[200px_auto_1fr]">
          <label className="grid gap-1 text-xs font-black uppercase tracking-wide text-muted">
            Expires in
            <select
              value={expiresInHours}
              onChange={(e) => setExpiresInHours(Number(e.target.value))}
              className="rounded-lg border border-line bg-white px-3 py-2 text-sm font-extrabold text-ink focus:outline-none focus:ring-1 focus:ring-brand"
              disabled={auditor}
            >
              {HOURS_OPTIONS.map((h) => (
                <option key={h} value={h}>
                  {h === 1
                    ? "1 hour"
                    : h < 24
                      ? `${h} hours`
                      : `${h / 24} day${h === 24 ? "" : "s"}`}
                </option>
              ))}
            </select>
          </label>
          <Button
            variant="primary"
            onClick={issue}
            disabled={createShare.isPending || auditor}
          >
            {createShare.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Share2 className="h-4 w-4" />
            )}{" "}
            Issue share
          </Button>
          {createdToken && (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-900">
              <div className="flex items-center justify-between gap-2 font-black">
                <span>New token (shown once)</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => copy(createdToken.token ?? "")}
                >
                  <ClipboardCopy className="h-3 w-3" /> Copy
                </Button>
              </div>
              <code className="mt-2 block break-all rounded bg-white p-2 font-mono text-[11px] text-ink">
                {createdToken.token}
              </code>
              <div className="mt-1">
                share_id{" "}
                <code className="text-ink">{createdToken.share_id}</code> ·
                expires {createdToken.expires_at}
              </div>
            </div>
          )}
        </div>
      </Card>

      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle>{(shares.data ?? []).length} active shares</CardTitle>
          <CardDescription>
            Revoking a share appends a revocation record; future probes with
            that token fail and the share drops from this list.
          </CardDescription>
        </CardHeader>
        <div className="grid gap-2 p-5 pt-0">
          {(shares.data ?? []).length === 0 && (
            <div className="rounded-lg border border-dashed border-line p-3 text-xs text-muted">
              No active shares. Issue one above to start.
            </div>
          )}
          {(shares.data ?? []).map((share) => (
            <div
              key={share.share_id}
              className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3 rounded-xl border border-line bg-white p-3 text-sm"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <code className="font-black text-ink">{share.share_id}</code>
                  <Badge tone={share.expired ? "critical" : "ready"}>
                    {share.expired ? "expired" : "active"}
                  </Badge>
                  <Badge>{share.scope}</Badge>
                </div>
                <div className="mt-1 text-xs text-muted">
                  created by <b className="text-ink">{share.created_by}</b> at{" "}
                  {share.created_at} · expires {share.expires_at}
                </div>
                <div className="mt-1 text-[10px] text-muted">
                  hash{" "}
                  <code className="text-ink">
                    {share.token_sha256.slice(0, 24)}…
                  </code>
                </div>
              </div>
              <Button
                variant="default"
                size="sm"
                disabled={auditor || revoke.isPending}
                onClick={async () => {
                  try {
                    await revoke.mutateAsync(share.share_id);
                    flash(`Revoked ${share.share_id}.`);
                  } catch (err) {
                    flash(`Revoke failed: ${(err as Error).message}`);
                  }
                }}
              >
                <XCircle className="h-3 w-3" /> Revoke
              </Button>
            </div>
          ))}
        </div>
      </Card>

      {toast && (
        <div className="fixed bottom-6 left-1/2 z-[70] -translate-x-1/2 rounded-lg bg-ink px-3.5 py-3 text-sm text-white shadow-hero">
          {toast}
        </div>
      )}
    </div>
  );
}
