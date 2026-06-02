import PublicTrustView from "./PublicTrustView";

// Static export needs a build-time param set for the dynamic segment. The real
// token is runtime-only, so we emit a single placeholder page; the Python
// server serves this prebuilt HTML for any `/console/trust/<token>` path and
// the client reads the actual token from the live URL.
export function generateStaticParams(): Array<{ token: string }> {
  return [{ token: "share" }];
}

export const dynamicParams = false;

export default function PublicTrustPage() {
  return <PublicTrustView />;
}
