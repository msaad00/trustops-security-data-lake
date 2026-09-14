import { expect, test } from "@playwright/test";

test("accepted invite replaces the token URL with console sign-in", async ({
  page,
}) => {
  await page.route("**/api/v1/invites/accept", (route) =>
    route.fulfill({
      json: { data: { email: "reviewer@example.test" } },
    }),
  );
  await page.goto("/console/dashboard/");
  await page.goto("/console/invite/?token=synthetic-invite");
  await page
    .getByRole("textbox", { name: "Display name" })
    .fill("Synthetic reviewer");
  const accepted = page.waitForRequest("**/api/v1/invites/accept");
  await page.getByRole("button", { name: "Join workspace" }).click();
  expect((await accepted).postDataJSON()).toEqual({
    token: "synthetic-invite",
    display_name: "Synthetic reviewer",
  });
  await expect(page).toHaveURL(/\/console\/login\/$/);
  await page.goBack();
  await expect(page).toHaveURL(/\/console\/dashboard\/$/);
});
