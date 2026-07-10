"use client";

import { useState } from "react";
import Link from "next/link";
import { Building2, Loader2 } from "lucide-react";
import { TrustOpsLogo } from "@/components/brand/TrustOpsLogo";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api/client";
import { notify } from "@/lib/toast";

export default function SignupPage() {
  const [orgSlug, setOrgSlug] = useState("");
  const [orgName, setOrgName] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [adminName, setAdminName] = useState("");
  const [planTier, setPlanTier] = useState("starter");
  const [pending, setPending] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setPending(true);
    try {
      const result = await api.signup({
        org_slug: orgSlug,
        org_name: orgName,
        admin_email: adminEmail,
        admin_name: adminName,
        plan_tier: planTier,
      });
      notify.success(`Workspace ${String(result.org_slug ?? orgSlug)} created`);
      window.location.assign("/console/login/");
    } catch (err) {
      notify.error(String((err as Error).message));
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="mx-auto grid min-h-screen max-w-lg place-items-center px-4 py-10">
      <Card className="w-full">
        <CardHeader>
          <TrustOpsLogo className="mb-3 h-8 w-auto" />
          <CardTitle className="flex items-center gap-2">
            <Building2 className="h-5 w-5 text-brand" />
            Create workspace
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-3" onSubmit={submit}>
            <label className="grid gap-1 text-sm">
              <span className="font-bold text-ink">Organization slug</span>
              <input
                required
                value={orgSlug}
                onChange={(e) => setOrgSlug(e.target.value)}
                className="rounded-lg border border-line px-3 py-2"
                placeholder="acme-security"
              />
            </label>
            <label className="grid gap-1 text-sm">
              <span className="font-bold text-ink">Organization name</span>
              <input
                required
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                className="rounded-lg border border-line px-3 py-2"
                placeholder="Acme Security"
              />
            </label>
            <label className="grid gap-1 text-sm">
              <span className="font-bold text-ink">Admin email</span>
              <input
                required
                type="email"
                value={adminEmail}
                onChange={(e) => setAdminEmail(e.target.value)}
                className="rounded-lg border border-line px-3 py-2"
              />
            </label>
            <label className="grid gap-1 text-sm">
              <span className="font-bold text-ink">Admin name</span>
              <input
                value={adminName}
                onChange={(e) => setAdminName(e.target.value)}
                className="rounded-lg border border-line px-3 py-2"
              />
            </label>
            <label className="grid gap-1 text-sm">
              <span className="font-bold text-ink">Plan</span>
              <select
                value={planTier}
                onChange={(e) => setPlanTier(e.target.value)}
                className="rounded-lg border border-line px-3 py-2"
              >
                <option value="starter">Starter</option>
                <option value="growth">Growth</option>
                <option value="enterprise">Enterprise</option>
              </select>
            </label>
            <Button type="submit" variant="primary" disabled={pending}>
              {pending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                "Create workspace"
              )}
            </Button>
          </form>
          <p className="mt-4 text-sm text-muted">
            Already have access?{" "}
            <Link href="/login" className="font-bold text-brand underline">
              Sign in
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
