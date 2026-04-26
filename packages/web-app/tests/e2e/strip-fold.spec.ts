/**
 * E2E happy-path test for the kinemind strip fold viewer.
 *
 * Scenarios:
 *   1. Page loads and title is visible
 *   2. Hinge slider moves and updates the UI
 *   3. 3D Canvas element is present
 *   4. Coupling heatmap is rendered
 */

import { expect, test } from "@playwright/test";

test.describe("kinemind strip fold", () => {
  test.beforeEach(async ({ page }) => {
    // Vite dev server serves at /; GH Pages uses /kinemind/
    await page.goto("/");
    // Wait for app to hydrate
    await page.waitForSelector("h1", { timeout: 10_000 });
  });

  test("page loads with kinemind title", async ({ page }) => {
    await expect(page).toHaveTitle(/kinemind/);
    const h1 = page.getByRole("heading", { level: 1 });
    await expect(h1).toBeVisible();
  });

  test("hinge slider is interactive and updates angle display", async ({ page }) => {
    // Find the first hinge slider by aria-label
    const slider = page.getByRole("slider", { name: /Hinge 1 angle/i });
    await expect(slider).toBeVisible();

    // Move slider to max value
    await slider.fill(String(Math.PI));

    // The angle display (degrees) should reflect the change
    // Accept any non-zero degree value indicating the slider moved
    const angleDisplay = page.locator('[aria-live="polite"][aria-atomic="true"]').first();
    await expect(angleDisplay).not.toHaveText("0.0°");
  });

  test("3D Canvas element is rendered", async ({ page }) => {
    const canvas = page.locator("canvas");
    await expect(canvas).toBeVisible({ timeout: 8_000 });
  });

  test("coupling heatmap SVG is visible", async ({ page }) => {
    const heatmapRegion = page.getByRole("region", {
      name: /Coupling matrix heatmap/i,
    });
    await expect(heatmapRegion).toBeVisible();

    const svg = heatmapRegion.locator("svg");
    await expect(svg).toBeVisible();
  });

  test("export trial button is present and accessible", async ({ page }) => {
    const btn = page.getByRole("button", { name: /Export Trial JSON/i });
    await expect(btn).toBeVisible();
    await expect(btn).toBeEnabled();
  });
});
