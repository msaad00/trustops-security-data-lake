import { expect, test } from "@playwright/test";

const BANNER = /Can.t reach the assessment API/;

test("a disabled feature (501) does not raise the API health banner", async ({
  page,
}) => {
  await page.route("**/api/v1/platform/usage", (route) =>
    route.fulfill({ status: 501, json: { detail: "not enabled" } }),
  );
  await page.goto("/console/auth/");
  await expect(page.getByText("Current session")).toBeVisible();
  await expect(page.getByText(BANNER)).toHaveCount(0);
  await expect(page.getByText("Hosted plan usage")).toHaveCount(0);
});

test("a real API failure raises the API health banner", async ({ page }) => {
  await page.route("**/api/v1/platform/usage", (route) =>
    route.fulfill({ status: 500, json: { detail: "boom" } }),
  );
  await page.goto("/console/auth/");
  await expect(page.getByText(BANNER)).toBeVisible();
});
