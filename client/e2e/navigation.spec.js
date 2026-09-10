import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
test.skip(
  !process.env.LAB_E2E_PASSWORD,
  "Configura una cuenta ficticia ADMIN, MANAGER y CLIENT con empresa/proyecto ficticios.",
);
test("navegación, recepción parcial e informes inmediatos", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByLabel("Correo electrónico")
    .fill(process.env.LAB_E2E_EMAIL || "admin@example.com");
  await page
    .getByLabel("Contraseña", { exact: true })
    .fill(process.env.LAB_E2E_PASSWORD);
  await page.getByRole("button", { name: "Ingresar", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Carga actual", exact: true }),
  ).toBeVisible();
  const session = await (await page.request.get("/api/session")).json();
  const headers = {
    Origin: process.env.LAB_E2E_URL || "http://localhost:5173",
    "X-CSRF-Token": session.csrf,
  };
  const projects = await (await page.request.get("/api/projects")).json();
  const catalog = await (await page.request.get("/api/catalog")).json();
  const created = await page.request.post("/api/requests", {
    headers,
    data: {
      project_id: projects[0].id,
      title: "Revisión visual " + Date.now(),
      samples: [
        { client_code: "VIS-01", assay_ids: [catalog[0].id] },
        {
          client_code: "VIS-02",
          notes: "Mezcla de componentes A y B",
          assay_ids: [catalog[0].id],
        },
      ],
    },
  });
  expect(created.ok()).toBeTruthy();
  let request = await created.json();
  for (const action of ["submit", "approve"]) {
    const response = await page.request.post(
      "/api/requests/" + request.id + "/actions",
      { headers, data: { version: request.version, action } },
    );
    expect(response.ok()).toBeTruthy();
    request = await response.json();
  }
  const out = path.resolve("../.local/review");
  fs.mkdirSync(out, { recursive: true });
  await page.reload();
  await expect(
    page.getByRole("heading", {
      name: "Carga abierta por tipo de ensayo",
      exact: true,
    }),
  ).toBeVisible();
  await page.screenshot({
    path: path.join(out, "dashboard.png"),
    fullPage: true,
  });
  await page.getByRole("link", { name: "Recepción", exact: true }).click();
  await expect(page).toHaveURL(/\/reception$/);
  await page.getByLabel("Buscar solicitud").fill(request.code);
  await page
    .getByRole("link", { name: "Registrar recepción", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Registrar recepción", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Custodia", exact: true }),
  ).toHaveCount(0);
  await page.locator("form").getByRole("checkbox", { name: /VIS-01/ }).check();
  await page
    .getByLabel("Transporte", { exact: true })
    .fill("Transporte de demostración");
  await page.getByLabel("Cantidad recibida (kg)", { exact: true }).fill("12");
  await page.getByLabel("Código de recepción", {exact:true}).fill("REC-QA-" + Date.now());
  await page.getByLabel("Código de laboratorio", {exact:true}).fill("LAB-QA-" + Date.now());
  await page
    .getByRole("button", { name: "Guardar recepción", exact: true })
    .click();
  await expect(
    page.locator("form").getByRole("checkbox", { name: /VIS-01/ }),
  ).not.toBeChecked();
  await page.screenshot({
    path: path.join(out, "reception.png"),
    fullPage: true,
  });
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Registrar recepción", exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Volver a la lista" }).click();
  await expect(page).toHaveURL(/\/reception\?q=/);
  await page
    .getByRole("link", { name: "Trabajo de laboratorio", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Trabajo de laboratorio", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Estado", { exact: true }).selectOption("PENDING");
  await page.reload();
  await expect(page.getByLabel("Estado", { exact: true })).toHaveValue(
    "PENDING",
  );
  await expect(
    page.getByRole("heading", { name: "Ensayos y programación", exact: true }),
  ).toBeVisible();
  await page.screenshot({ path: path.join(out, "work.png"), fullPage: true });
  await page.getByRole("link", { name: "Informes", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Informes", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Buscar solicitud aprobada").fill(request.code);
  await expect(
    page
      .getByLabel("Solicitud de destino")
      .getByRole("option", { name: new RegExp(request.code) }),
  ).toHaveCount(1);
  await page.getByLabel("Solicitud de destino").selectOption(request.id);
  await page
    .getByLabel("Cargar informe PDF (máximo 20 MB)")
    .setInputFiles(path.resolve("e2e/fixtures/informe-demo.pdf"));
  await page.getByRole("button", { name: "Subir y compartir informe" }).click();
  await page
    .getByLabel("Buscar informe por solicitud o proyecto")
    .fill(request.code);
  await expect(
    page.getByRole("button", { name: "Descargar", exact: true }),
  ).toHaveCount(1);
  await page.screenshot({
    path: path.join(out, "reports.png"),
    fullPage: true,
  });
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Descargar", exact: true }).click();
  expect((await download).suggestedFilename()).toBe("Informe-1.pdf");
  await page.getByRole("link", { name: request.code, exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Informes PDF", exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Informes PDF", exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Volver a la lista" }).click();
  await expect(page).toHaveURL(/\/reports\?q=/);
  await page.setViewportSize({ width: 900, height: 1100 });
  await expect(
    page.getByRole("button", { name: "Descargar", exact: true }),
  ).toHaveCount(1);
  await page.screenshot({ path: path.join(out, "tablet.png"), fullPage: true });
});
