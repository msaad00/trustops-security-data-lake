"use client";

import { KeyRound, LogIn, ShieldCheck, Terminal } from "lucide-react";
import { AuthMark } from "@/components/auth/AuthMark";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuthMethods } from "@/lib/api/hooks";
import type { AuthMethod } from "@/lib/api/types";

function BrowserMethodCard({ method }: { method: AuthMethod }) {
  return (
    <div className="grid gap-3 rounded-xl border border-line bg-white p-4">
      <div className="flex flex-wrap items-center gap-3">
        <AuthMark
          providerKind={method.provider_kind}
          methodId={method.id}
          size="lg"
          providerLabel={method.provider_label}
        />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-black text-ink">{method.label}</span>
            <Badge tone={method.configured ? "ready" : "attention"}>
              {method.configured ? "configured" : "not configured"}
            </Badge>
            {method.protocol && (
              <Badge tone="info">{method.protocol}</Badge>
            )}
          </div>
          {method.issuer_host && (
            <p className="mt-1 truncate text-xs text-muted">
              IdP host: <code className="text-ink">{method.issuer_host}</code>
            </p>
          )}
        </div>
      </div>
      {method.setup_hint && (
        <p className="text-xs leading-5 text-muted">{method.setup_hint}</p>
      )}
      <div className="flex flex-wrap gap-2 text-[11px] text-muted">
        {method.tenant_slug && (
          <span className="rounded-full border border-line bg-panel px-2 py-0.5">
            tenant: {method.tenant_slug}
          </span>
        )}
        <span className="rounded-full border border-line bg-panel px-2 py-0.5">
          auto-provision: {method.auto_provision ? "on" : "off"}
        </span>
        {method.metadata_url && (
          <a
            href={method.metadata_url}
            className="rounded-full border border-line bg-panel px-2 py-0.5 font-bold text-brand hover:underline"
          >
            metadata
          </a>
        )}
      </div>
      {method.configured && method.id !== "api_key" && (
        <Button asChild variant="primary" size="lg">
          <a href={method.login_url}>
            <LogIn className="h-4 w-4" />
            {method.label}
          </a>
        </Button>
      )}
    </div>
  );
}

export default function LoginPage() {
  const auth = useAuthMethods();
  const data = auth.data;
  const browserMethods =
    data?.methods.filter(
      (method) => method.id === "oidc" || method.id === "saml",
    ) ?? [];
  const configured = browserMethods.filter((method) => method.configured);
  const apiKeyMethod = data?.methods.find((method) => method.id === "api_key");

  return (
    <section className="grid min-h-screen place-items-center p-6">
      <div className="grid w-full max-w-[980px] gap-5 lg:grid-cols-[1fr_420px]">
        <div className="rounded-2xl border border-[#1e334a] bg-[#07111e] p-8 text-white shadow-hero">
          <Badge tone="info" className="mb-5 bg-cyan-100 text-cyan-800">
            Server mode
          </Badge>
          <h1 className="max-w-[680px] text-4xl font-black leading-[1.04]">
            Sign in with your company identity provider.
          </h1>
          <p className="mt-4 max-w-[620px] text-base leading-7 text-slate-300">
            Browser sessions use the same tenant, RBAC scopes, and request audit
            trail as API keys. OIDC and SAML resolve to one local user record —
            no parallel auth silo.
          </p>
          <div className="mt-8 grid gap-3 sm:grid-cols-3">
            {[
              "Tenant scoped",
              "RBAC enforced",
              "Audit logged",
            ].map((label) => (
              <div
                key={label}
                className="rounded-lg border border-white/15 bg-white/5 p-3 text-sm font-extrabold text-slate-100"
              >
                <ShieldCheck className="mb-2 h-4 w-4 text-cyan-300" />
                {label}
              </div>
            ))}
          </div>
        </div>

        <Card className="self-stretch">
          <CardHeader>
            <CardTitle>Identity providers</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3">
            {auth.isPending && (
              <div className="rounded-lg border border-line bg-slate-50 p-4 text-sm font-bold text-muted">
                Checking identity providers...
              </div>
            )}

            {!auth.isPending &&
              configured.map((method) => (
                <BrowserMethodCard key={method.id} method={method} />
              ))}

            {!auth.isPending && configured.length === 0 && (
              <div className="rounded-lg border border-line bg-slate-50 p-4">
                <div className="flex items-start gap-3">
                  <Terminal className="mt-0.5 h-5 w-5 text-muted" />
                  <div>
                    <div className="font-black text-ink">
                      No browser SSO provider is configured.
                    </div>
                    <p className="mt-1 text-sm leading-6 text-muted">
                      Mount OIDC or SAML environment variables on the server.
                      Agents and CI can still authenticate with API keys.
                    </p>
                  </div>
                </div>
                {browserMethods.map((method) => (
                  <div key={method.id} className="mt-3">
                    <BrowserMethodCard method={method} />
                  </div>
                ))}
              </div>
            )}

            {apiKeyMethod && (
              <div className="rounded-xl border border-dashed border-line bg-panel p-4">
                <div className="flex items-center gap-2 text-sm font-black text-ink">
                  <KeyRound className="h-4 w-4 text-brand" />
                  Headless access
                </div>
                <p className="mt-2 text-xs leading-5 text-muted">
                  {apiKeyMethod.setup_hint}
                </p>
                <code className="mt-2 block truncate rounded-md bg-white px-2 py-1 text-[11px] text-ink">
                  POST {apiKeyMethod.login_url}
                </code>
              </div>
            )}

            {auth.isError && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm font-bold text-amber-900">
                Auth discovery is unavailable on this server.
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
