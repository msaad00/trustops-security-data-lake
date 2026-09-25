import { expect, test } from "@playwright/test";

test("on phones the sign-in options come before the product panel", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/console/login/");
  const providers = page.getByText("Identity providers", { exact: true });
  await expect(providers).toBeInViewport();
  const productPanel = page.locator("section > div > div").first();
  const [formTop, panelTop] = await Promise.all([
    providers.evaluate((el) => el.getBoundingClientRect().top),
    productPanel.evaluate((el) => el.getBoundingClientRect().top),
  ]);
  expect(formTop).toBeLessThan(panelTop);
});
