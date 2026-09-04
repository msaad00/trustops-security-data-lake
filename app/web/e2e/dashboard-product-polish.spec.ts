import { test, expect } from "@playwright/test";

test.describe("dashboard product polish", () => {
  test("presents a coherent trust command center", async ({ page }) => {
    await page.goto("/console/dashboard/");

    const commandCenter = page.getByRole("region", {
      name: "Assessment summary",
    });
    await expect(commandCenter).toBeVisible({ timeout: 20_000 });
    await expect(
      commandCenter.getByText("Assessment summary", { exact: true }),
    ).toBeVisible();
    await expect(
      commandCenter.getByRole("region", { name: "Evidence operating loop" }),
    ).toBeVisible();
    const frameworkMark = commandCenter
      .getByRole("img", { name: /framework$/ })
      .first();
    await expect(frameworkMark).toBeVisible();
    await expect(frameworkMark.locator("svg")).toHaveCount(0);

    for (const stage of ["Collect", "Evaluate", "Operate", "Prove"]) {
      await expect(
        commandCenter.getByText(stage, { exact: true }),
      ).toBeVisible();
    }
  });

  test("keeps workspace and theme controls available on desktop", async ({
    page,
  }) => {
    await page.goto("/console/dashboard/");
    await expect(
      page.getByRole("button", { name: /account menu/i }),
    ).toBeVisible({ timeout: 20_000 });
  });

  test("keeps the command center usable in mobile dark mode", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.addInitScript(() => {
      window.localStorage.setItem("trustops:theme", JSON.stringify("dark"));
    });
    await page.goto("/console/dashboard/");

    await expect(page.locator("html")).toHaveClass(/dark/);
    await expect(
      page.getByRole("region", { name: "Assessment summary" }),
    ).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("Critical gaps need owners")).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
  });
});
