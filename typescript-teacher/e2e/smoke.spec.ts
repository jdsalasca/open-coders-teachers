import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("la app renderiza sin violaciones de accesibilidad", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "TypeScript teacher" })).toBeVisible();
  const button = page.getByRole("button", { name: "Incrementar" });
  await expect(button).toBeVisible();

  await button.click();
  await expect(page.locator('[data-role="value"]')).toHaveText("1");

  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});
