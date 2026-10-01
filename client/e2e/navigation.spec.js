import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
test.skip(
  !process.env.LAB_E2E_PASSWORD,
  "Requiere datos ficticios con esquema 4.",
);
test("navegación directa, filtros persistentes y descarga privada", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("Correo electrónico").fill("admin@example.com");
  await page
    .getByLabel("Contraseña", { exact: true })
    .fill(process.env.LAB_E2E_PASSWORD);
  await page.getByRole("button", { name: "Ingresar", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Carga actual", exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Recepción", exact: true }).click();
  await page.getByLabel("Buscar solicitud").fill("SOL-DEMO-001");
  await page.getByLabel("Estado de recepción").selectOption("NOT_RECEIVED");
  await expect(
    page.getByRole("link", { name: "Registrar recepción", exact: true }),
  ).toHaveCount(1);
  await page.reload();
  await expect(page.getByLabel("Estado de recepción")).toHaveValue(
    "NOT_RECEIVED",
  );
  await page
    .getByRole("link", { name: "Registrar recepción", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Registrar recepción", exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Registrar recepción", exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: /Volver a la lista/ }).click();
  await expect(page).toHaveURL(/reception\?.*condition=NOT_RECEIVED/);
  await page.goto(
    "/requests/40000000-0000-0000-0000-000000000001?tab=documents",
  );
  await page
    .getByLabel("Cargar informe PDF (máximo 20 MB)")
    .setInputFiles(path.resolve("e2e/fixtures/informe-demo.pdf"));
  await page.getByRole("button", { name: "Subir y compartir informe" }).click();
  await expect(
    page.getByRole("button", { name: "Descargar", exact: true }).first(),
  ).toBeVisible();
  const download = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Descargar", exact: true })
    .first()
    .click();
  expect((await download).suggestedFilename()).toMatch(/^Informe-\d+\.pdf$/);
  const session = await (await page.request.get("/api/session")).json();
  expect(session.user.roles).toContain("ADMIN");
  await page.goto("/work?state=RUNNING&request_q=SOL-DEMO-001");
  await expect(page.getByLabel("Estado", { exact: true })).toHaveValue(
    "RUNNING",
  );
  await page.reload();
  await expect(page.getByLabel("Estado", { exact: true })).toHaveValue(
    "RUNNING",
  );
  await expect(
    page.getByRole("cell", { name: "En ejecución", exact: true }),
  ).toBeVisible();
  await page.goto("/reports?q=SOL-DEMO-001");
  await expect(
    page.getByRole("button", { name: "Descargar", exact: true }).first(),
  ).toBeVisible();
  fs.mkdirSync(path.resolve("../.local/review-v4"), { recursive: true });
  await page.screenshot({
    path: path.resolve("../.local/review-v4/report-filter.png"),
    fullPage: true,
  });
});
