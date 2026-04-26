import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/**
 * Vite configuration for kinemind web-app.
 * - base="/kinemind/" for GitHub Pages deployment.
 * - React plugin enables Fast Refresh and JSX transform.
 */
export default defineConfig({
  base: "/kinemind/",
  plugins: [react()],
  resolve: {
    alias: {
      "@": "/src",
    },
  },
  optimizeDeps: {
    exclude: ["@kinemind/core-math", "@kinemind/shared-types"],
  },
  server: {
    port: 5173,
    strictPort: false,
  },
});
