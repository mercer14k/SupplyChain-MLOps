import { afterEach, expect, it, vi } from "vitest";
import { api, mutation } from "./api";
afterEach(() => vi.unstubAllGlobals());
it("surfaces server error evidence", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ error: { message: "Model must be approved" } }),
    }),
  );
  await expect(api("/training")).rejects.toThrow("Model must be approved");
});
it("sends a role token and idempotency key for mutations", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValue({ ok: true, json: async () => ({ id: "job" }) });
  vi.stubGlobal("fetch", fetch);
  await mutation("/training", { task: "forecast" }, "temporary-token");
  const request = fetch.mock.calls[0][1];
  expect(request.headers.Authorization).toBe("Bearer temporary-token");
  expect(request.headers["Idempotency-Key"]).toBeTruthy();
  expect(request.method).toBe("POST");
});
