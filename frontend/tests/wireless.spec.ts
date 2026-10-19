import { test, expect } from "@playwright/test";
const evidence =
  process.env.WIRELESS_EVIDENCE_DIR || "../wireless-lab/evidence/browser";
test("guest enters, executes failure, explores packet evidence and exports", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/?lab=wireless");
  await page.getByRole("button", { name: "Continue as Guest" }).click();
  await expect(
    page.getByRole("heading", { name: "Wireless overview", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("DEMO MODE", { exact: true })).toBeVisible();
  await expect(
    page.getByText("association success", { exact: true }).first(),
  ).toBeVisible();
  await page.screenshot({ path: `${evidence}/overview.png`, fullPage: true });
  await page
    .getByRole("button", { name: "Automated test scenarios", exact: true })
    .click();
  await page
    .locator(".wl-scenario")
    .filter({ hasText: "AP association rejection" })
    .getByRole("button", { name: "Run scenario", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "association rejected", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Validation pass", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Export investigation JSON" }),
  ).toHaveAttribute("href", /format=json/);
  await page.screenshot({
    path: `${evidence}/investigation.png`,
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Packet trace explorer", exact: true })
    .click();
  await page.getByRole("button", { name: /Load A:/ }).click();
  await page
    .getByRole("textbox", { name: "Filter packet events" })
    .fill("eapol");
  await expect(page.locator("tbody tr")).toHaveCount(4);
  await page.screenshot({ path: `${evidence}/packets.png`, fullPage: true });
  const denied = await page.request.post("/api/wireless-lab/uploads", {
    headers: { "X-Wireless-Demo": "1" },
    data: "invalid",
  });
  expect(denied.status()).toBe(403);
  expect(errors).toEqual([]);
});
test("mobile guest session and all seven views remain usable", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/?lab=wireless");
  await page.getByRole("button", { name: "Continue as Guest" }).click();
  await expect(
    page.getByRole("heading", { name: "Wireless overview", exact: true }),
  ).toBeVisible();
  for (const name of [
    "Virtual access points",
    "Client connection timeline",
    "Packet trace explorer",
    "Automated test scenarios",
    "Failure investigation",
    "Analytics and reports",
  ]) {
    await page.getByRole("button", { name, exact: true }).click();
    await expect(
      page.getByRole("heading", { name, exact: true }),
    ).toBeVisible();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(390);
  }
  await page.screenshot({ path: `${evidence}/mobile.png`, fullPage: true });
});
