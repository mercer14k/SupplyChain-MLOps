import { test, expect, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
const root = path.resolve(import.meta.dirname, "../../..");
const credentials = () =>
  JSON.parse(
    fs.readFileSync(path.join(root, ".runtime/e2e/credentials.json"), "utf8"),
  ) as Record<string, string>;
async function access(page: Page, role: "operator" | "reviewer") {
  await page.getByRole("button", { name: /Manage workspace access/ }).click();
  await page.getByLabel("Workspace key").fill(credentials()[role]);
  await page.getByRole("button", { name: "Connect workspace" }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
}
async function inspect(page: Page, id: string) {
  await page.getByRole("button", { name: /Model registry/ }).click();
  await page.getByRole("button", { name: `Review ${id}`, exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Model evidence & promotion" }),
  ).toBeVisible();
}

test("train, independently approve, deploy, infer, monitor and restore a prior version", async ({
  page,
  request,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const ds = (
    await (await request.get("http://127.0.0.1:8019/api/v1/datasets")).json()
  ).items.find((d: { name: string }) => d.name === "demand.jsonl");
  const queued = await request.post("http://127.0.0.1:8019/api/v1/training", {
    data: { dataset_id: ds.id, task: "forecast" },
    headers: {
      Authorization: `Bearer ${credentials().operator}`,
      "Idempotency-Key": crypto.randomUUID(),
    },
  });
  const job = await queued.json();
  await expect
    .poll(
      async () =>
        (
          await (
            await request.get(`http://127.0.0.1:8019/api/v1/jobs/${job.id}`)
          ).json()
        ).status,
    )
    .toBe("succeeded");
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Model operations", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("img", { name: /Observed demand/ }),
  ).toBeVisible();
  const original = (
    await (
      await request.get("http://127.0.0.1:8019/api/v1/runs?task=forecast")
    ).json()
  ).items.find((r: { stage: string }) => r.stage === "candidate");
  expect(original).toBeTruthy();
  await page.screenshot({
    path: path.join(root, "docs/screenshots/overview.png"),
    fullPage: true,
  });
  await access(page, "reviewer");
  await inspect(page, original.id);
  await page
    .getByLabel("Decision reason")
    .fill("Reviewed holdout accuracy, source lineage and quality gate.");
  await page.getByRole("button", { name: "Approve candidate" }).click();
  await expect(
    page.getByRole("button", { name: "Deploy model" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Deploy model" }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Close dialog" }).click();
  await access(page, "operator");
  await inspect(page, original.id);
  await page
    .getByLabel("Decision reason")
    .fill("Deploy reviewed baseline for the local operations demo.");
  await page.getByRole("button", { name: "Deploy model" }).click();
  await expect(
    page.getByRole("dialog").getByText("production", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page.getByRole("button", { name: "Inference", exact: true }).click();
  await page.getByRole("button", { name: "Run forecast" }).click();
  await expect(page.getByText(/Prediction recorded/)).toBeVisible();
  const before = (
    await (await request.get("http://127.0.0.1:8019/api/v1/predictions")).json()
  ).items[0];
  await page.getByRole("button", { name: "Monitoring", exact: true }).click();
  await page.getByRole("button", { name: "Evaluate a batch" }).click();
  await page.getByRole("button", { name: "Run drift evaluation" }).click();
  await expect(
    page.getByText("Drift detected", { exact: true }).first(),
  ).toBeVisible();
  await page.screenshot({
    path: path.join(root, "docs/screenshots/monitoring.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "New training run" }).click();
  await page.getByLabel("Ridge alpha").fill("2");
  const queuedNext = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/v1/training") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Queue training run" }).click();
  const nextJob = await (await queuedNext).json();
  await expect
    .poll(
      async () =>
        (
          await (
            await request.get(`http://127.0.0.1:8019/api/v1/jobs/${nextJob.id}`)
          ).json()
        ).status,
    )
    .toBe("succeeded");
  const finishedJob = await (
    await request.get(`http://127.0.0.1:8019/api/v1/jobs/${nextJob.id}`)
  ).json();
  const challenger = await (
    await request.get(`http://127.0.0.1:8019/api/v1/runs/${finishedJob.run_id}`)
  ).json();
  await page.getByRole("button", { name: "Refresh data" }).click();
  await access(page, "reviewer");
  await inspect(page, challenger.id);
  await page
    .getByLabel("Decision reason")
    .fill("Reviewed challenger against the weekly baseline.");
  await page.getByRole("button", { name: "Approve candidate" }).click();
  await expect(
    page.getByRole("button", { name: "Deploy model" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close dialog" }).click();
  await access(page, "operator");
  await inspect(page, challenger.id);
  await page
    .getByLabel("Decision reason")
    .fill("Deploy the approved challenger for rollback verification.");
  await page.getByRole("button", { name: "Deploy model" }).click();
  await expect(
    page.getByRole("dialog").getByText("production", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close dialog" }).click();
  await inspect(page, original.id);
  await page
    .getByLabel("Decision reason")
    .fill("Restore the previously deployed baseline and verify exact output.");
  await page.getByRole("button", { name: "Roll back to this version" }).click();
  await expect(
    page.getByRole("dialog").getByText("production", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page.getByRole("button", { name: "Inference", exact: true }).click();
  await page.getByRole("button", { name: "Run forecast" }).click();
  await expect(page.getByText(/Prediction recorded/)).toBeVisible();
  const after = (
    await (await request.get("http://127.0.0.1:8019/api/v1/predictions")).json()
  ).items[0];
  expect(after.results).toEqual(before.results);
  expect(after.artifact_sha256).toBe(before.artifact_sha256);
  await page.getByRole("button", { name: "Retraining", exact: true }).click();
  await page.getByRole("button", { name: "New schedule" }).click();
  await page.getByRole("button", { name: "Create schedule" }).click();
  await expect(page.getByText("Every 1440 minutes").first()).toBeVisible();
  await page.getByRole("button", { name: "Audit trail", exact: true }).click();
  await expect(
    page.getByText("model rolled back", { exact: true }).first(),
  ).toBeVisible();
  expect(errors).toEqual([]);
});

test("invalid data evidence and mobile navigation remain accessible", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Dataset versions", exact: true })
    .click();
  await page.getByLabel("Search datasets").fill("invalid");
  await expect(
    page.getByRole("button", { name: /invalid.jsonl/ }),
  ).toBeVisible();
  await page.getByRole("button", { name: /invalid.jsonl/ }).click();
  await expect(
    page.getByText("Validation failure", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page.getByRole("button", { name: "Architecture", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "From experiment to operation" }),
  ).toBeVisible();
  const width = await page.evaluate(() => ({
    scroll: document.documentElement.scrollWidth,
    viewport: innerWidth,
  }));
  expect(width.scroll).toBeLessThanOrEqual(width.viewport);
  await page.screenshot({
    path: path.join(root, "docs/screenshots/mobile.png"),
    fullPage: true,
  });
});
