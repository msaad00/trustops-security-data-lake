import { test, expect } from "@playwright/test";

const CONNECTOR_ID = "github-security";

async function ensureConnectorDisabled(
  request: import("@playwright/test").APIRequestContext,
) {
  const response = await request.get("/api/v1/connectors");
  expect(response.ok()).toBeTruthy();
  const connectors = (await response.json()).data ?? [];
  const connector = connectors.find(
    (item: { connector_id?: string }) => item.connector_id === CONNECTOR_ID,
  );
  if (connector?.state !== "enabled") return;
  const disable = await request.post(
    `/api/v1/connectors/${CONNECTOR_ID}/configure`,
    { data: { state: "disabled", actor: "e2e" } },
  );
  expect(disable.ok()).toBeTruthy();
}

test.describe("connectors workflow", () => {
  test("probe-gated enable flow for github-security", async ({
    page,
    request,
  }) => {
    await ensureConnectorDisabled(request);

    await page.goto(`/console/connectors/?connect=${CONNECTOR_ID}`);
    await expect(page.getByRole("main")).toBeVisible({ timeout: 20_000 });

    await expect(
      page
        .getByRole("dialog")
        .getByRole("heading", { name: "GitHub Security" }),
    ).toBeVisible({ timeout: 15_000 });

    await page
      .getByLabel(/GitHub App installation token env/i)
      .fill("TRUSTOPS_GITHUB_APP_INSTALLATION_TOKEN");
    await page.getByLabel(/Repository \(owner\/name\)/i).fill("acme/platform");

    const dialog = page.getByRole("dialog");
    await expect(
      dialog.getByRole("button", { name: "Enable connector" }),
    ).toHaveCount(0);

    await dialog.getByRole("button", { name: "Test connection" }).click();
    const enableBtn = dialog.getByRole("button", {
      name: "Enable connector",
    });
    await expect(enableBtn).toBeEnabled({ timeout: 15_000 });

    await enableBtn.click();
    await expect(page.getByText(/GitHub Security enabled/i)).toBeVisible({
      timeout: 15_000,
    });
    await expect(
      dialog.getByRole("button", { name: "Sync now" }),
    ).toBeVisible();

    const listResponse = await request.get("/api/v1/connectors");
    expect(listResponse.ok()).toBeTruthy();
    const connectors = (await listResponse.json()).data ?? [];
    const enabled = connectors.find(
      (item: { connector_id?: string }) => item.connector_id === CONNECTOR_ID,
    );
    expect(enabled?.state).toBe("enabled");
  });

  test("control eval runs from dashboard source sync panel", async ({
    page,
  }) => {
    await page.goto("/console/dashboard/");
    await expect(page.getByRole("main")).toBeVisible({ timeout: 20_000 });

    const ingestionToggle = page.getByRole("button", {
      name: /Source sync & control eval/i,
    });
    if ((await ingestionToggle.getAttribute("aria-expanded")) !== "true") {
      await ingestionToggle.click();
    }

    await page.getByRole("button", { name: "Run control eval" }).click();
    await expect(
      page.getByText(
        /Control eval complete|Control eval failed|Control eval finished/i,
      ),
    ).toBeVisible({
      timeout: 30_000,
    });
  });
});
