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
    await expect(page.getByText("Trust Command Center")).toBeVisible();
    await expect(
      page.getByText("Failing tests", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("Critical findings", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("Stale evidence", { exact: true }),
    ).toBeVisible();
  });

  test("audit room shows readiness score", async ({ page }) => {
    await page.goto("/console/audit-room/");
    await expect(page.getByRole("main")).toBeVisible({ timeout: 20_000 });
    await expect(
      page.getByRole("heading", { level: 1, name: "Audit readiness room" }),
    ).toBeVisible();
    await expect(page.getByText("Audit score", { exact: true })).toBeVisible();
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
