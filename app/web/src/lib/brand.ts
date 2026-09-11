/** Trust Data Lake product identity — single source for UI copy and metadata. */

export const BRAND = {
  /** Customer-facing product name. */
  name: "Trust Data Lake",
  /** Wordmark segments used for the product lockup. */
  wordmarkPrimary: "Trust Data",
  wordmarkAccent: "Lake",
  /** Human console surface. */
  consoleName: "Trust Data Lake Console",
  /** Category line used in README and marketing-adjacent docs. */
  category: "The trust layer for security data lakes",
  /** One-line mission for meta tags and share cards. */
  tagline:
    "Normalize security evidence, evaluate controls, and prove trust continuously.",
  /** Headless-first differentiator. */
  surfaces: "API · CLI · MCP · CI · Console",
  /** Short description for Open Graph / npm / package manifests. */
  description:
    "Customer-owned security data lake infrastructure for normalized evidence, deterministic control evaluations, and continuous trust proof.",
  /** Public trust-center header subtitle. */
  trustShareTitle: "Trust Data Lake Trust Center",
  /** Repo / PyPI technical name (not customer-facing). */
  packageName: "trustops-security-data-lake",
  /** CLI command (operator surface, not product rename). */
  cliCommand: "security-lakehouse",
  version: "0.2.7",
  colors: {
    blue: "#4f7cff",
    cyan: "#30c7d2",
    ink: "#101623",
  },
  repoUrl: "https://github.com/msaad00/trustops-security-data-lake",
  mcpServerName: "trustops",
  mcpCommand: "trustops-mcp",
  /** Dashboard home eyebrow (feature area, not product name). */
  homeEyebrow: "Home",
  /** Short label under the wordmark in chrome. */
  consoleSubtitle: "Security trust layer",
} as const;
