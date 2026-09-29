import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5188,
    strictPort: true,
    proxy: {
      "/api": {
        target: process.env.SCML_API_URL || "http://127.0.0.1:8018",
        changeOrigin: false,
      },
      "/health": "http://127.0.0.1:8018",
      "/ready": "http://127.0.0.1:8018",
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test-setup.ts"],
    include: ["src/**/*.test.tsx", "src/**/*.test.ts"],
  },
});
