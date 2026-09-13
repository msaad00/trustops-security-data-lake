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
  await expect
    .poll(() =>
      marks.evaluateAll(
        (nodes) =>
          nodes.length >= 3 &&
          nodes.every(
            (node) => node.querySelectorAll("g[transform]").length === 4,
          ),
      ),
    )
    .toBe(true);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect
    .poll(() =>
      marks.evaluateAll(
        (nodes) =>
          nodes.length >= 3 &&
          nodes.every(
            (node) => node.querySelectorAll("g[transform]").length === 4,
          ),
      ),
    )
    .toBe(true);
});
