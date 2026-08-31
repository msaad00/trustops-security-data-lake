import { test, expect } from "@playwright/test";

test.describe("console smoke", () => {
  test("dashboard shows trust home shell", async ({ page }) => {
    await page.goto("/console/dashboard/");
    await expect(page.getByRole("main")).toBeVisible({ timeout: 20_000 });
    await expect(
      page.getByRole("heading", {
        level: 1,
        name: /^Executive trust overview$/,
      }),
    ).toBeVisible();
    await expect(page.getByText("TrustOps overview")).toBeVisible();
    await expect(page.getByText("Framework posture")).toBeVisible();
    await expect(
      page.getByText("Control pass rate", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("Open findings", { exact: true }),
    ).toBeVisible();
    await expect(page.getByText("Proof export", { exact: true })).toBeVisible();
    await expect(
      page.getByRole("tab", { name: "Posture", exact: true }),
    ).toHaveAttribute("aria-selected", "true");
    await expect(
      page.getByRole("tab", { name: "Sources", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("tab", { name: "Proof", exact: true }),
    ).toBeVisible();
    await expect(page.getByText("Scale tier")).toHaveCount(0);
  });

  test("audit room shows readiness score", async ({ page }) => {
    await page.goto("/console/audit-room/");
    await expect(page.getByRole("main")).toBeVisible({ timeout: 20_000 });
    await expect(
      page.getByRole("heading", { level: 1, name: "Audit readiness room" }),
    ).toBeVisible();
    await expect(page.getByText("Audit score", { exact: true })).toBeVisible();
    await expect(
      page.getByRole("tab", { name: "Freshness", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("tab", { name: "Runs", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("tab", { name: "Snapshots", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("tab", { name: "Gaps", exact: true }),
    ).toBeVisible();
  });

  test("evidence page separates facts from report exports", async ({
    page,
  }) => {
    await page.goto("/console/evidence/");
    await expect(page.getByRole("main")).toBeVisible({ timeout: 20_000 });
    await expect(
      page.getByRole("heading", {
        level: 1,
        name: "Normalized evidence facts",
      }),
    ).toBeVisible();
    await expect(
      page.getByText("These rows are evidence facts, not reports."),
    ).toBeVisible();
    await expect(page.getByText("Security data lake layers")).toBeVisible();
    await expect(page.getByText("Bronze raw -> Silver facts")).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Manage schedules" }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Open audit room" }),
    ).toBeVisible();
  });

  test("core trust pages share pipeline orientation", async ({ page }) => {
    for (const [path, active] of [
      ["/console/frameworks/", "Framework map"],
      ["/console/controls/", "Control eval"],
      ["/console/violations/", "Findings"],
    ] as const) {
      await page.goto(path);
      const pipeline = page.getByLabel("Trust pipeline");
      await expect(pipeline).toBeVisible({ timeout: 20_000 });
      await expect(pipeline.getByText("Evidence facts")).toBeVisible();
      await expect(pipeline.getByText(active, { exact: true })).toBeVisible();
      await expect(pipeline.locator('[aria-current="page"]')).toContainText(
        active,
      );
    }
  });

  test("frameworks render governed identity assets", async ({ page }) => {
    await page.goto("/console/frameworks/");

    const nistArtwork = page
      .getByRole("img", {
        name: /NIST AI Risk Management Framework 1\.0 official framework artwork/,
      })
      .first();
    await expect(nistArtwork).toBeVisible();
    await expect(nistArtwork.locator("img")).toHaveAttribute(
      "src",
      "/console/frameworks/nist-ai-rmf.png",
    );

    await expect(
      page
        .getByRole("img", {
          name: /ISO\/IEC 27001:2022 framework scope label; not an official logo/,
        })
        .first(),
    ).toBeVisible();
  });

  test("dashboard progressively discloses operational detail", async ({
    page,
  }) => {
    await page.goto("/console/dashboard/");
    await expect(page.getByRole("main")).toBeVisible({ timeout: 20_000 });
    const detail = page.getByRole("button", { name: /Operational detail/ });
    await expect(detail).toHaveAttribute("aria-expanded", "false");
    await detail.click();
    await expect(detail).toHaveAttribute("aria-expanded", "true");
    await expect(page.getByText("Framework readiness")).toBeVisible();
  });

  test("default navigation exposes the full trust workflow", async ({
    page,
  }) => {
    await page.goto("/console/dashboard/");
    const sidebar = page.getByRole("complementary");

    for (const label of [
      "Overview",
      "Insights",
      "Connections",
      "Evidence",
      "Access reviews",
      "Vendor risk",
      "Controls",
      "Frameworks",
      "Findings",
      "Risk register",
      "Policies",
      "AI governance",
      "Crosswalk",
      "Remediation",
      "Workflows",
      "Agents",
      "Audit room",
      "Trust center",
      "Audit log",
    ]) {
      await expect(sidebar.getByRole("link", { name: label })).toBeVisible();
    }

    for (const label of [
      "Onboarding",
      "Launch",
      "Demo",
      "Deploy",
      "Agent harness",
      "Pricing",
    ]) {
      await expect(sidebar.getByRole("link", { name: label })).toHaveCount(0);
    }
  });

  test("shell exposes skip link and main landmark", async ({ page }) => {
    await page.goto("/console/dashboard/");
    await expect(page.getByRole("main")).toBeVisible({ timeout: 20_000 });
    const skip = page.getByRole("link", { name: "Skip to main content" });
    await expect(skip).toHaveAttribute("href", "#main-content");
    await skip.focus();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/#main-content$/);
    await expect(page.locator("#main-content")).toBeVisible();
  });

  test("health endpoint responds while console is served", async ({
    request,
  }) => {
    const response = await request.get("/api/v1/healthz");
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body.data).toMatchObject({
      ok: true,
      service: "trustops-assessment",
    });
  });
});
