import { expect, test } from "@playwright/test";

test("the app shell uses the approved evidence-lake mark at every size", async ({
  page,
}) => {
  await page.goto("/console/dashboard/");
  await expect(
    page.getByRole("heading", { name: "Dashboard", exact: true }),
  ).toBeVisible();
  const marks = page.locator('svg[aria-label="TrustOps"]');
  expect(await marks.count()).toBeGreaterThanOrEqual(3);
  for (const mark of await marks.all()) {
    await expect(mark.locator("g[transform]")).toHaveCount(4);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  for (const mark of await marks.all()) {
    await expect(mark.locator("g[transform]")).toHaveCount(4);
  }
});
