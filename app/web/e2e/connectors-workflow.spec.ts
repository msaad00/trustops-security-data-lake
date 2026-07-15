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
  test("AWS starts as a compact authorization workspace", async ({
    page,
    request,
  }) => {
    await request.post("/api/v1/connectors/aws-posture/configure", {
      data: { state: "disabled", actor: "e2e" },
    });
    await page.goto("/console/connectors/?connect=aws-posture");

    const dialog = page.getByRole("dialog");
    await expect(
      dialog.getByRole("heading", { name: "AWS Posture" }),
    ).toBeVisible({ timeout: 15_000 });
    const activeAuthorization = dialog.getByRole("button", {
      name: /Connect cloud account|Test connection/,
    });
    await expect(activeAuthorization).toHaveCount(1);
    await expect(activeAuthorization).toBeVisible();
    await expect(dialog.getByText("Scheduled sync")).toBeHidden();

    const box = await activeAuthorization.boundingBox();
    expect(box).not.toBeNull();
    expect((box?.y ?? 0) + (box?.height ?? 0)).toBeLessThanOrEqual(720);
  });

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
      dialog.getByRole("button", { name: "Sync evidence" }),
    ).toBeVisible();

    const listResponse = await request.get("/api/v1/connectors");
    expect(listResponse.ok()).toBeTruthy();
    const connectors = (await listResponse.json()).data ?? [];
    const enabled = connectors.find(
      (item: { connector_id?: string }) => item.connector_id === CONNECTOR_ID,
    );
    expect(enabled?.state).toBe("enabled");
  });

  test("control eval runs from dashboard sources view", async ({ page }) => {
    await page.goto("/console/dashboard/");
    await expect(page.getByRole("main")).toBeVisible({ timeout: 20_000 });
    await expect(
      page.getByRole("tab", { name: "Posture", exact: true }),
    ).toHaveAttribute("aria-selected", "true");

    await page.getByRole("tab", { name: "Sources", exact: true }).click();
    await expect(
      page.getByRole("tab", { name: "Sources", exact: true }),
    ).toHaveAttribute("aria-selected", "true");
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
