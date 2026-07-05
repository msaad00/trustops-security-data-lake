#!/usr/bin/env node
/**
 * Capture console screenshots for README / docs.
 * Requires: server at TRUSTOPS_SCREENSHOT_URL (default http://127.0.0.1:8787)
 *           and `npx playwright install chromium` once.
 */
import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const base =
  process.env.TRUSTOPS_SCREENSHOT_URL?.replace(/\/$/, "") ||
  "http://127.0.0.1:8787";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..", "..");
const outDir = path.join(root, "docs", "images");

/** [filename, route, optional setup fn] */
const shots = [
  ["trustops-demo-dashboard.png", "/console/dashboard/"],
  ["trustops-demo-audit-room.png", "/console/audit-room/"],
  ["trustops-demo-evidence.png", "/console/evidence/"],
  ["trustops-demo-insights.png", "/console/insights/"],
  ["trustops-demo-connectors.png", "/console/connectors/"],
  ["trustops-demo-frameworks.png", "/console/frameworks/"],
  ["trustops-demo-policies.png", "/console/policies/"],
  ["trustops-demo-vendor-risk.png", "/console/vendor-risk/"],
  ["trustops-demo-workflows.png", "/console/automation/"],
  ["trustops-demo-trust-center.png", "/console/trust-center/"],
  ["trustops-demo-onboarding.png", "/console/onboarding/"],
  ["trustops-demo-auth.png", "/console/auth/"],
  ["trustops-demo-graph.png", "/console/graph/"],
  ["trustops-demo-control-drawer.png", "/console/controls/", "control-drawer"],
];

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await mkdir(outDir, { recursive: true });

async function waitForShell() {
  await page.waitForSelector("main", { timeout: 20_000 });
  await page.waitForTimeout(3500);
}

for (const entry of shots) {
  const [file, route, setup] = entry;
  const url = `${base}${route}`;
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45_000 });
  await waitForShell();

  if (setup === "control-drawer") {
    const row = page.locator("button").filter({ hasText: /SOC2|CC6|NIST/i }).first();
    if (await row.count()) {
      await row.click();
      await page.waitForTimeout(1500);
    }
  }

  await page.screenshot({
    path: path.join(outDir, file),
    fullPage: false,
  });
  console.log("wrote", file);
}

await browser.close();
