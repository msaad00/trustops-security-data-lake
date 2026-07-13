import { test, expect } from "@playwright/test";

test.describe("agents harness", () => {
  test("fixture-mode posture review surfaces proposed writes", async ({
    page,
    request,
  }) => {
    const create = await request.post("/api/v1/agent-runs", {
      data: {
        harness: "posture_review",
        objective: "e2e fixture review",
        use_model: false,
        idempotency_key: `e2e-posture-${Date.now()}`,
      },
    });
    expect(create.ok()).toBeTruthy();
    const run = (await create.json()).data;
    expect(run.mode).toBe("rules_only");
    expect(run.decisions.length).toBeGreaterThan(0);

    await page.goto("/console/agents/");
    await expect(page.getByRole("main")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByRole("heading", { name: "Governed runs" })).toBeVisible();
    await expect(page.getByText(/fixture/i).first()).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByRole("button", { name: "Approve" }).first()).toBeVisible();

    const approve = await request.post(
      `/api/v1/agent-runs/${run.id}/decisions/0/approve`,
      { data: { note: "e2e approve" } },
    );
    expect(approve.ok()).toBeTruthy();
    expect((await approve.json()).data.decisions[0].status).toBe("executed");
  });
});
