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

const shots = [
  ["trustops-demo-dashboard.png", "/console/dashboard/"],
  ["trustops-demo-audit-room.png", "/console/audit-room/"],
  ["trustops-demo-evidence.png", "/console/evidence/"],
  ["trustops-demo-auth.png", "/console/auth/"],
  ["trustops-demo-connectors.png", "/console/connectors/"],
  ["trustops-demo-frameworks.png", "/console/frameworks/"],
  ["trustops-demo-workflows.png", "/console/automation/"],
  ["trustops-demo-trust-center.png", "/console/trust-center/"],
  ["trustops-demo-graph.png", "/console/graph/"],
  ["trustops-demo-control-drawer.png", "/console/controls/"],
];

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await mkdir(outDir, { recursive: true });

for (const [file, route] of shots) {
  const url = `${base}${route}`;
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30_000 });
  await page.waitForTimeout(2500);
  await page.screenshot({
    path: path.join(outDir, file),
    fullPage: false,
  });
  console.log("wrote", file);
}

await browser.close();
