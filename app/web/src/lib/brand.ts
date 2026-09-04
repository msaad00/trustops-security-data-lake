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
  category: "Open evidence infrastructure for GRC",
  /** One-line mission for meta tags and share cards. */
  tagline:
    "Collect evidence, evaluate controls, operate findings, and prove continuously — same JSON everywhere.",
  /** Headless-first differentiator. */
  surfaces: "API · CLI · MCP · CI · Console",
  /** Short description for Open Graph / npm / package manifests. */
  description:
    "Open-source, headless-first evidence infrastructure for customer-owned GRC data — SOC 2, NIST AI RMF, FedRAMP, ISO, and beyond.",
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
  consoleSubtitle: "Console",
} as const;
