import { expect, test } from "@playwright/test";

test("the app shell uses the approved evidence-lake mark at every size", async ({
  page,
}) => {
  await page.goto("/console/dashboard/");
  await expect(
    page.getByRole("heading", { name: "Dashboard", exact: true }),
  ).toBeVisible();
  const marks = page.locator(
    'header svg[aria-label="TrustOps"], aside svg[aria-label="TrustOps"], nav[aria-label="Breadcrumb"] svg[aria-label="TrustOps"]',
  );
  await expect(marks).toHaveCount(4);
  await expect
    .poll(() =>
      marks.evaluateAll(
        (nodes) =>
          nodes.length === 4 &&
          nodes.every(
            (node) => node.querySelectorAll("g[transform]").length === 4,
          ),
      ),
    )
    .toBe(true);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("button", { name: "Sidebar is compact on small screens" }),
  ).toBeVisible();
  await expect
    .poll(() =>
      marks.evaluateAll(
        (nodes) =>
          nodes.length === 2 &&
          nodes.every(
            (node) => node.querySelectorAll("g[transform]").length === 4,
          ),
      ),
    )
    .toBe(true);
});
