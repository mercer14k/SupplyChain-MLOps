import { defineConfig } from "@playwright/test";
import path from "node:path";
const root = path.resolve(import.meta.dirname, "../..");
const python =
  process.env.SCML_PYTHON ||
  path.join(
    root,
    ".venv",
    process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
  );
export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  fullyParallel: false,
  timeout: 60000,
  use: {
    baseURL: "http://127.0.0.1:5189",
    viewport: { width: 1512, height: 982 },
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: `"${python}" scripts/test_backend.py`,
      cwd: root,
      url: "http://127.0.0.1:8019/ready",
      reuseExistingServer: false,
      env: {
        SCML_STATE_DIR: path.join(root, ".runtime/e2e"),
        SCML_LLM_ENABLED: "false",
      },
    },
    {
      command: "node node_modules/vite/bin/vite.js --port 5189",
      url: "http://127.0.0.1:5189",
      reuseExistingServer: false,
      env: { SCML_API_URL: "http://127.0.0.1:8019" },
    },
  ],
});
