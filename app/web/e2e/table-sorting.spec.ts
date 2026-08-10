import { expect, test } from "@playwright/test";

const scoreColumn = async (page: import("@playwright/test").Page) => {
  const rows = page.locator("table tbody tr");
  await expect.poll(async () => await rows.count()).toBeGreaterThan(1);
  return await rows.evaluateAll((trs) =>
    trs
      .map((tr) => tr.querySelectorAll("td")[4]?.textContent?.trim() ?? "")
      .filter(Boolean),
  );
};

test("violations table sorts by score and toggles direction", async ({
  page,
}) => {
  await page.goto("/console/violations/");

  const initial = await scoreColumn(page);
  const nums = initial.map(Number).filter((n) => !Number.isNaN(n));
  expect(nums.length).toBeGreaterThan(1);

  // Default sorting state is severity_score desc.
  expect([...nums].sort((a, b) => b - a)).toEqual(nums);

  await page.getByRole("columnheader", { name: /Score/i }).click();
  const asc = (await scoreColumn(page)).map(Number).filter((n) => !isNaN(n));
  expect([...asc].sort((a, b) => a - b)).toEqual(asc);
  expect(asc).not.toEqual(nums);
});

test("evidence table re-sorts when a header is clicked", async ({ page }) => {
  await page.goto("/console/evidence/");
  const rows = page.locator("table tbody tr");
  await expect.poll(async () => await rows.count()).toBeGreaterThan(1);

  const before = await rows.first().textContent();
  await page.getByRole("columnheader").nth(1).click();
  await expect
    .poll(async () => await rows.first().textContent())
    .not.toBe(before);
});
