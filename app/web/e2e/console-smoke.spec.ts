import { test, expect } from "@playwright/test";

test.describe("console smoke", () => {
  test("dashboard shows trust home shell", async ({ page }) => {
    await page.goto("/console/dashboard/");
    await expect(page.getByRole("main")).toBeVisible({ timeout: 20_000 });
    await expect(
      page.getByRole("navigation", { name: "Koda Home shortcuts" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", {
        level: 1,
        name: /^Executive trust overview$/,
      }),
    ).toBeVisible();
    await expect(page.getByText("Trust Command Center")).toBeVisible();
  });

  test("audit room shows readiness score", async ({ page }) => {
    await page.goto("/console/audit-room/");
    await expect(page.getByRole("main")).toBeVisible({ timeout: 20_000 });
    await expect(
      page.getByRole("heading", { level: 1, name: "Audit readiness room" }),
    ).toBeVisible();
    await expect(page.getByText("Audit score", { exact: true })).toBeVisible();
  });

  test("trust home shortcut navigates to audit room", async ({ page }) => {
    await page.goto("/console/dashboard/");
    await expect(page.getByRole("main")).toBeVisible({ timeout: 20_000 });
    await page
      .getByRole("navigation", { name: "Koda Home shortcuts" })
      .getByRole("link", { name: "Audit room" })
      .click();
    await expect(page).toHaveURL(/\/console\/audit-room\/?$/);
    await expect(
      page.getByRole("heading", { level: 1, name: "Audit readiness room" }),
    ).toBeVisible();
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
