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
const root = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
  "..",
  "..",
);
const outDir = path.join(root, "docs", "images");

/** [filename, route, optional setup fn] */
const shots = [
  ["trustops-demo-dashboard.png", "/console/dashboard/"],
  ["trustops-demo-findings.png", "/console/violations/"],
  ["trustops-demo-remediation.png", "/console/remediation/"],
  ["trustops-demo-triage.png", "/console/violations/", "finding-drawer"],
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

/** Dark variants only for the images the README shows via <picture>. */
const darkVariants = new Set([
  "trustops-demo-dashboard.png",
  "trustops-demo-evidence.png",
  "trustops-demo-frameworks.png",
  "trustops-demo-triage.png",
  "trustops-demo-graph.png",
]);
const themes = (process.env.TRUSTOPS_SCREENSHOT_THEMES || "light,dark").split(
  ",",
);
const browser = await chromium.launch();
await mkdir(outDir, { recursive: true });
let page;

async function waitForShell() {
  await page.waitForSelector("main", { timeout: 20_000 });
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(1200);
}

const requested = new Set(process.argv.slice(2));
const selected = requested.size
  ? shots.filter(([file]) => requested.has(file))
  : shots;
if (requested.size && selected.length !== requested.size)
  throw new Error("Unknown screenshot filename");
for (const theme of themes) {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    colorScheme: theme,
  });
  await context.addInitScript((mode) => {
    localStorage.setItem("trustops:theme", JSON.stringify(mode));
  }, theme);
  page = await context.newPage();
  for (const entry of selected) {
    const [baseFile, route, setup] = entry;
    if (theme !== "light" && !darkVariants.has(baseFile)) continue;
    const file =
      theme === "light"
        ? baseFile
        : baseFile.replace(/\.png$/, `-${theme}.png`);
    const url = `${base}${route}`;
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45_000 });
    await waitForShell();

    if (setup === "finding-drawer") {
      await page
        .getByRole("button", { name: /Review finding/ })
        .first()
        .click();
      await page.getByRole("dialog").waitFor();
      await page.waitForTimeout(500);
    }
    if (setup === "control-drawer") {
      const row = page
        .locator("button")
        .filter({ hasText: /SOC2|CC6|NIST/i })
        .first();
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
  await context.close();
}

await browser.close();
