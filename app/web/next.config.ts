import type { NextConfig } from "next";

// Static export so `npm run build` emits a fully static bundle into
// src/security_lakehouse/web/dist/ — Python wheel ships it, no Node in prod.
// basePath '/console' matches the Python server route.
//
// Build/dev run with `--webpack` (see package.json scripts): Next 16 defaults
// to Turbopack, which rejects a `distDir` that escapes the project root
// ("distDirRoot should not navigate out of the projectPath"). The console must
// emit straight into the Python package tree (../../src/.../web/dist), so we
// stay on the Webpack builder, which supports the out-of-project distDir.
const config: NextConfig = {
  output: "export",
  basePath: "/console",
  assetPrefix: "/console",
  trailingSlash: true,
  distDir: "../../src/security_lakehouse/web/dist",
  cleanDistDir: true,
  images: { unoptimized: true },
  reactStrictMode: true,
  typescript: { ignoreBuildErrors: false },
};

export default config;
