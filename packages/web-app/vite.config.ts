import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

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
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          "three-r3f": ["three", "@react-three/fiber", "@react-three/drei"],
          "core-math": ["@kinemind/core-math"],
        },
      },
    },
  },
  server: {
    port: 5173,
    strictPort: false,
  },
});
