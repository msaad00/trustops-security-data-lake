import type { AuthMethods } from "@/lib/api/types";

export interface SignInTarget {
  href: string;
  label: string;
  external: boolean;
}

/** Resolve where "Sign in" should go — never link to OIDC unless it is configured. */
export function resolveSignInTarget(
  auth: AuthMethods | undefined,
): SignInTarget {
  if (auth && !auth.require_auth) {
    return { href: "/dashboard", label: "Open console", external: false };
  }

  const configuredSso = auth?.methods.find(
    (method) =>
      (method.id === "oidc" || method.id === "saml") && method.configured,
  );
  if (configuredSso) {
    return {
      href: configuredSso.login_url,
      label: "Sign in to workspace",
      external: configuredSso.login_url.startsWith("http"),
    };
  }

  return { href: "/login", label: "Sign in", external: false };
}
