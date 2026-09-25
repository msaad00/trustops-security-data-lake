import { expect, test } from "@playwright/test";

test("crosswalk mappings are paginated and the page stays scannable", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/console/crosswalk/");
  const status = page.getByText(/^Showing 1–25 of \d+ mappings$/);
  await expect(status).toBeVisible();

  await page.getByRole("button", { name: "Next page" }).click();
  await expect(page.getByText(/^Showing 26–50 of \d+ mappings$/)).toBeVisible();

  await page
    .getByPlaceholder(/search/i)
    .first()
    .fill("CC6.1");
  await expect(page.getByText(/^Showing 1–\d+ of \d+ mappings$/)).toBeVisible();

  await page
    .getByPlaceholder(/search/i)
    .first()
    .fill("");
  await page
    .locator("details")
    .evaluateAll((els) =>
      els.forEach((el) => ((el as HTMLDetailsElement).open = true)),
    );
  const height = await page.evaluate(
    () => document.documentElement.scrollHeight,
  );
  expect(height).toBeLessThan(12000);
});
