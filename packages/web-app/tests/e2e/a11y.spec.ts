/**
 * Accessibility (a11y) E2E test using axe-core.
 * Checks for WCAG 2.0 A and AA violations on page load.
 */

import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test.describe("accessibility", () => {
  test("no WCAG 2.0 A/AA violations on page load", async ({ page }) => {
    await page.goto("/");
    // Wait for the app to hydrate
    await page.waitForSelector("h1", { timeout: 10_000 });

    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();

    expect(results.violations).toEqual([]);
  });
});
