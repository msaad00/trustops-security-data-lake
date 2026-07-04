/** TrustOps product identity — single source for UI copy and metadata. */

export const BRAND = {
  /** Customer-facing product name. Always one word: TrustOps */
  name: "TrustOps",
  /** Human console surface (not "Workbench" or "Assessment Console"). */
  consoleName: "TrustOps Console",
  /** Category line used in README and marketing-adjacent docs. */
  category: "Open-source trust operations",
  /** One-line mission for meta tags and share cards. */
  tagline:
    "Turn evidence in your lake into live compliance posture, audit-ready snapshots, and shareable proof.",
  /** Headless-first differentiator. */
  surfaces: "API · CLI · MCP · CI · Console",
  /** Short description for Open Graph / npm / package manifests. */
  description:
    "Open-source, headless-first trust operations for customer-owned evidence lakes — SOC 2, NIST AI RMF, FedRAMP, ISO, and beyond.",
  /** Public trust-center header subtitle. */
  trustShareTitle: "TrustOps Trust Center",
  /** Repo / PyPI technical name (not customer-facing). */
  packageName: "trustops-security-data-lake",
  /** CLI command (operator surface, not product rename). */
  cliCommand: "security-lakehouse",
  version: "0.2.0",
  colors: {
    blue: "#4f7cff",
    cyan: "#30c7d2",
    ink: "#101623",
  },
  repoUrl: "https://github.com/msaad00/trustops-security-data-lake",
} as const;
