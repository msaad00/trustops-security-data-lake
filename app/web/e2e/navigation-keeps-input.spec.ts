import { expect, test } from "@playwright/test";

test("input typed right after client navigation is not thrown away", async ({
  page,
  request,
}) => {
  const res = await request.get("/api/v1/violations?limit=1");
  const finding = (await res.json()).data[0];
  await page.goto(
    `/console/violations/?id=${encodeURIComponent(String(finding.violation_id))}`,
  );
  await page
    .getByRole("dialog")
    .getByRole("link", { name: /Create task/ })
    .click();

  const title = page.getByRole("textbox", { name: "Task title", exact: true });
  await title.fill("typed immediately after navigation");
  await page.waitForTimeout(1000);

  await expect(title).toHaveValue("typed immediately after navigation");
});
