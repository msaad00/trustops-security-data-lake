import { expect, test } from "@playwright/test";

// The server caps a single page at 500 rows (MAX_PAGE_LIMIT). 600 total means
// a correct client makes two requests; a client that reads one page renders
// 500 and reports success, which is the regression this guards.
const TOTAL = 600;
const PAGE = 500;

const violation = (i: number) => ({
  violation_id: `V-${String(i).padStart(4, "0")}`,
  control_id: "SOC2-CC6.1",
  asset_id: `asset-${i}`,
  asset_owner: "platform",
  event_type: "access_review",
  severity: "high",
  severity_score: (i % 100) + 1,
  source: "synthetic",
  evidence_ref: `ev-${i}`,
  detected_at: "2026-08-10T00:00:00Z",
  environment: "prod",
  event_id: `e-${i}`,
});

test("the findings queue reads every page, not just the first", async ({
  page,
}) => {
  const offsets: number[] = [];

  await page.route("**/api/v1/violations*", async (route) => {
    const url = new URL(route.request().url());
    const offset = Number(url.searchParams.get("offset") ?? "0");
    const limit = Number(url.searchParams.get("limit") ?? "100");
    offsets.push(offset);

    const data = Array.from(
      { length: Math.max(0, Math.min(limit, TOTAL - offset)) },
      (_, i) => violation(offset + i),
    );

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        data,
        meta: {
          api_version: "v1",
          resource: "violations",
          count: TOTAL,
          returned: data.length,
          limit,
          offset,
        },
        errors: [],
      }),
    });
  });

  await page.goto("/console/violations/");
  await page.waitForSelector("table tbody tr");

  await expect(page.getByText(`${TOTAL} open violations`)).toBeVisible();
  await expect
    .poll(async () => page.locator("table tbody tr").count())
    .toBe(TOTAL);

  // Two requests, and the second one asked for the tail.
  expect(offsets).toEqual([0, PAGE]);
});
