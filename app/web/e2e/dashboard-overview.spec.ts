import { expect, test } from "@playwright/test";

test("header reflects healthy and unavailable API responses", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/console/dashboard/");
  const header = page.getByRole("banner");
  await expect(
    header.getByText("API connected", { exact: true }),
  ).toBeVisible();
  await page.route("**/api/v1/healthz", (route) =>
    route.fulfill({
      status: 503,
      json: { error: "Synthetic unavailable API" },
    }),
  );
  await header.getByRole("button", { name: "Refresh data" }).click();
  await expect(
    header.getByText("API unavailable", { exact: true }),
  ).toBeVisible();
});

test("assessment overview links to workspaces and discloses provenance", async ({
  page,
}) => {
  await page.goto("/console/dashboard/");
  const overview = page.getByRole("region", {
    name: "Current assessment",
    exact: true,
  });
  await expect(
    overview.getByRole("link", { name: /Open findings/ }),
  ).toHaveAttribute("href", "/console/violations/");
  await expect(
    overview.getByRole("link", { name: /Control pass rate/ }),
  ).toHaveAttribute("href", "/console/controls/");
  await expect(
    overview.getByRole("link", { name: /Assessment export/ }),
  ).toHaveAttribute("href", "/console/audit-room/");
  await expect(
    overview.getByText("Assessment ID", { exact: true }),
  ).not.toBeVisible();
  await overview.getByText("Assessment details", { exact: true }).click();
  await expect(
    overview.getByText("Assessment ID", { exact: true }),
  ).toBeVisible();
  await overview.getByText("Assessment details", { exact: true }).click();
  await expect(
    overview.getByText("Assessment ID", { exact: true }),
  ).not.toBeVisible();
});

test("compact app header keeps search and account actions usable on mobile", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/console/dashboard/");
  const header = page.getByRole("banner");
  await header.getByRole("button", { name: "Open command palette" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await header.getByRole("button", { name: /account menu/ }).click();
  await expect(page.getByRole("menu")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(
    header.getByRole("button", { name: "Capture snapshot" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
