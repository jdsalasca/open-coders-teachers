import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("la app renderiza sin violaciones de accesibilidad", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "React teacher" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Incrementar" })).toBeVisible();

  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});
