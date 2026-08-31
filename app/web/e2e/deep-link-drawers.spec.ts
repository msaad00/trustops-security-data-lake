import {
  test,
  expect,
  type APIRequestContext,
  type Page,
} from "@playwright/test";

async function firstRecord(
  request: APIRequestContext,
  endpoint: string,
): Promise<Record<string, unknown>> {
  const response = await request.get(endpoint);
  expect(response.ok()).toBeTruthy();
  const records = (await response.json()).data ?? [];
  expect(records.length).toBeGreaterThan(0);
  return records[0];
}

async function expectPaletteDeepLink(page: Page, path: string, id: string) {
  await page.getByRole("button", { name: "Open command palette" }).click();
  const palette = page.getByRole("dialog", { name: "Search" });
  await expect(palette).toBeVisible();
  await palette
    .getByPlaceholder(
      "Search controls, violations, evidence, workflows, routes…",
    )
    .fill(id);
  const result = palette.getByRole("button").filter({ hasText: id });
  await expect(result.first()).toBeVisible({ timeout: 15_000 });
  await result.first().click();

  await expect(page).toHaveURL(
    new RegExp(`${path.replaceAll("/", "\\/")}\\?id=${encodeURIComponent(id)}`),
  );
  await expect(
    page.getByRole("dialog").getByRole("heading", { name: id }),
  ).toBeVisible({ timeout: 15_000 });
}

test.describe("record deep links", () => {
  test("open the requested control, finding, and evidence drawers", async ({
    page,
    request,
  }) => {
    const control = await firstRecord(request, "/api/v1/controls");
    const violation = await firstRecord(request, "/api/v1/violations");
    const evidence = await firstRecord(request, "/api/v1/evidence");

    await page.goto("/console/dashboard/");
    await expect(page.getByRole("main")).toBeVisible({ timeout: 20_000 });

    await expectPaletteDeepLink(
      page,
      "/console/controls/",
      String(control.control_id),
    );
    const controlDialog = page.getByRole("dialog");
    await page.waitForTimeout(500);
    const openPosition = await controlDialog.evaluate(
      (element) => element.getBoundingClientRect().x,
    );
    await controlDialog.getByRole("button", { name: "Close" }).click();
    await page.waitForTimeout(80);
    const exitPosition = await controlDialog.evaluate(
      (element) => element.getBoundingClientRect().x,
    );
    expect(exitPosition).toBeGreaterThan(openPosition);
    await expect(controlDialog).toHaveCount(0);

    await expectPaletteDeepLink(
      page,
      "/console/violations/",
      String(violation.violation_id),
    );
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "Close" })
      .click();
    await expect(page.getByRole("dialog")).toHaveCount(0);

    await expectPaletteDeepLink(
      page,
      "/console/evidence/",
      String(evidence.event_id),
    );
  });
});
