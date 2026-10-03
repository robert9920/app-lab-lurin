import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
const output = path.resolve("../.local/review-v4");
let requestId;
test.describe.configure({ mode: "serial" });
test.skip(
  !process.env.LAB_E2E_PASSWORD,
  "Requiere cuentas ficticias y API con esquema 4.",
);
test.beforeAll(() => fs.mkdirSync(output, { recursive: true }));
async function login(page, email) {
  await page.goto("/");
  await page.getByLabel("Correo electrónico").fill(email);
  await page
    .getByLabel("Contraseña", { exact: true })
    .fill(process.env.LAB_E2E_PASSWORD);
  await page.getByRole("button", { name: "Ingresar", exact: true }).click();
  await expect(
    page.getByRole("navigation", { name: "Espacio de trabajo" }),
  ).toBeVisible();
}
async function general(page, title) {
  await page.getByLabel("Nombre de la solicitud").fill(title);
  for (const [field, value] of [
    ["Distrito", "Lurín"],
    ["Provincia", "Lima"],
    ["Departamento", "Lima"],
  ])
    await page.getByLabel(field + " *", { exact: true }).fill(value);
  await expect(
    page.getByLabel("Coordenadas Este (opcional)"),
  ).not.toHaveAttribute("required");
  await expect(
    page.getByLabel("Coordenadas Norte (opcional)"),
  ).not.toHaveAttribute("required");
  await page
    .getByRole("button", { name: "Continuar con las muestras" })
    .click();
}
test("matriz de 33 muestras, catálogo real y envío con coordenadas/ensayos vacíos", async ({
  page,
}) => {
  await login(page, "cliente@example.com");
  await page.getByRole("link", { name: "Solicitudes", exact: true }).click();
  await page.getByRole("link", { name: "Nueva solicitud" }).click();
  const project = page.getByRole("combobox", { name: "Proyecto *" });
  await project.fill("w51");
  await expect(page.getByRole("option").first()).toBeVisible();
  await page.getByRole("option").first().getByRole("button").click();
  await expect(project).toHaveValue(/W51/i);
  await page.screenshot({
    path: path.join(output, "general.png"),
    fullPage: true,
  });
  await general(page, "Revisión horizontal " + Date.now());
  await page.getByRole("button", { name: "Pegar Excel" }).click();
  const modal = page.getByRole("dialog");
  const rows = Array.from({ length: 33 }, (_, i) =>
    [
      `DH-${i + 1}`,
      `VIS-${i + 1}`,
      "1.25",
      "2.50",
      "Relaves",
      "2",
      "12.6",
      "Observación de muestra " + (i + 1),
    ].join("\t"),
  ).join("\n");
  await modal.getByRole("textbox").fill(rows);
  await modal.getByRole("button", { name: "Incorporar filas" }).click();
  await expect(
    page.getByLabel("Muestra * · fila 33", { exact: true }),
  ).toHaveValue("VIS-33");
  await page.screenshot({
    path: path.join(output, "matrix-33.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Revisar solicitud" }).click();
  await page
    .getByRole("button", { name: "Enviar al laboratorio", exact: true })
    .click();
  await page.waitForURL(/requests\/[0-9a-f-]{36}$/);
  await expect(
    page.getByRole("heading", { name: /Revisión horizontal/ }),
  ).toBeVisible();
  requestId = page.url().match(/requests\/([^/?]+)/)[1];
  const r = await (await page.request.get(`/api/requests/${requestId}`)).json();
  expect(r.status).toBe("WAITING_ASSAYS");
  expect(r.easting).toBeNull();
  expect(r.northing).toBeNull();
  expect(r.samples).toHaveLength(33);
  expect(Number(r.samples[0].weight)).toBe(12.6);
  await page.screenshot({
    path: path.join(output, "summary.png"),
    fullPage: true,
  });
});
test("recepción parcial, OT flexible y edición sin perder recepción", async ({
  page,
  browser,
}) => {
  await login(page, "jefe@example.com");
  await page.goto(`/requests/${requestId}?tab=reception`);
  await page.locator(".sample-editor").first().getByRole("checkbox").check();
  await page
    .getByLabel("Código de recepción", { exact: true })
    .fill("REC-VISUAL");
  await page
    .getByLabel("Código de laboratorio", { exact: true })
    .fill("LAB-VISUAL-" + Date.now());
  await page.getByLabel("Sacos recibidos (opcional)").fill("1");
  await page.getByLabel("Peso recibido (kg, opcional)").fill("6.3");
  await page
    .getByLabel("Condición", { exact: true })
    .selectOption("INSUFFICIENT");
  await page.getByLabel("Observaciones de recepción").fill("Falta un saco");
  await page.getByRole("button", { name: "Guardar recepción" }).click();
  await expect(
    page.getByRole("button", { name: "Generar OT", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Generar OT", exact: true }).click();
  await page.getByLabel("Código OT *").fill(" ot-visual ");
  await page.getByRole("button", { name: "Guardar OT" }).click();
  await expect(page.getByText("OT-VISUAL", { exact: true })).toBeVisible();
  await page.screenshot({
    path: path.join(output, "reception-ot.png"),
    fullPage: true,
  });
  const context = await browser.newContext();
  const client = await context.newPage();
  await login(client, "cliente@example.com");
  await client.goto(`/requests/${requestId}/edit`);
  await expect(client.getByLabel("Nombre de la solicitud")).toHaveValue(
    /Revisión horizontal/,
  );
  await client
    .getByRole("button", { name: "Continuar con las muestras" })
    .click();
  await expect(
    client.getByLabel("Sacos · fila 1", { exact: true }),
  ).toHaveAttribute("readonly");
  await client
    .getByRole("checkbox", { name: "Seleccionar todas las filas", exact: true })
    .check();
  await client
    .getByRole("checkbox", {
      name: "Aplicar Contenido de humedad a filas seleccionadas",
      exact: true,
    })
    .check();
  await client.getByRole("button", { name: "Revisar solicitud" }).click();
  await client
    .getByRole("button", { name: "Guardar y enviar a revisión" })
    .click();
  await client.waitForURL(/requests\/[0-9a-f-]{36}$/);
  await expect(
    client.getByRole("heading", { name: /Revisión horizontal/ }),
  ).toBeVisible();
  const r = await (
    await client.request.get(`/api/requests/${requestId}`)
  ).json();
  expect(r.status).toBe("SUBMITTED");
  expect(Number(r.samples[0].received_weight)).toBe(6.3);
  expect(Number(r.samples[0].quantity)).toBe(2);
  expect(r.tasks).toHaveLength(33);
  await context.close();
  await page.goto(`/requests/${requestId}`);
  await page.getByRole("button", { name: "Aprobar", exact: true }).click();
  await expect(page.getByText("Aprobado", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Ensayos", exact: true }).click();
  await page
    .getByRole("checkbox", { name: "Seleccionar todos", exact: true })
    .check();
  await page.getByLabel("Acción", { exact: true }).selectOption("assign");
  await page
    .getByLabel("Técnico", { exact: true })
    .selectOption({ label: "Lucía Torres" });
  await page.getByRole("button", { name: /Aplicar/ }).click();
  await expect(
    page.getByText("Selecciona uno o varios ensayos", { exact: false }),
  ).toBeVisible();
  await page.screenshot({
    path: path.join(output, "work-detail.png"),
    fullPage: true,
  });
  const fixture = path.resolve("e2e/fixtures/informe-demo.pdf");
  await page.getByRole("button", { name: "Documentos", exact: true }).click();
  await page
    .getByLabel("Cargar informe PDF (máximo 20 MB)")
    .setInputFiles(fixture);
  await page.getByRole("button", { name: "Subir y compartir informe" }).click();
  await expect(
    page.getByRole("button", { name: /Descargar/ }).first(),
  ).toBeVisible();
});
test("externos sin proyecto, administración editable y diseño adaptable", async ({
  page,
}) => {
  await login(page, "externo@example.com");
  await page.goto("/requests/new");
  await expect(page.getByRole("combobox", { name: "Proyecto *" })).toHaveCount(
    0,
  );
  await general(page, "Solicitud externa visual " + Date.now());
  await page.getByLabel("Muestra * · fila 1", { exact: true }).fill("EXT-VIS");
  await page
    .getByLabel("Tipo de muestra * · fila 1", { exact: true })
    .fill("Suelo");
  await page.getByRole("button", { name: "Revisar solicitud" }).click();
  await page
    .getByRole("button", { name: "Enviar al laboratorio", exact: true })
    .click();
  await page.waitForURL(/requests\/[0-9a-f-]{36}$/);
  await expect(
    page.getByRole("heading", { name: /Solicitud externa visual/ }),
  ).toBeVisible();
  const rid = page.url().match(/requests\/([^/?]+)/)[1];
  expect(
    (await (await page.request.get(`/api/requests/${rid}`)).json()).project_id,
  ).toBe("EXTERNO");
  await page.getByRole("button", { name: "Cerrar sesión" }).click();
  await login(page, "admin@example.com");
  await page.getByRole("link", { name: "Administración", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Proyectos", exact: true }),
  ).toHaveCount(0);
  const row = page.getByRole("row").filter({ hasText: "externo@example.com" });
  await row.getByRole("button", { name: "Editar", exact: true }).click();
  const modal = page.getByRole("dialog");
  await modal.getByLabel("Teléfono (opcional)").fill("999 555 111");
  await modal
    .getByLabel("Nombre *", { exact: true })
    .fill("Cliente externo actualizado");
  await modal.getByRole("button", { name: "Guardar registro" }).click();
  await expect(modal).toHaveCount(0);
  await expect(row).toContainText("999 555 111");
  await page.screenshot({
    path: path.join(output, "admin.png"),
    fullPage: true,
  });
  for (const [route, file] of [
    ["/requests", "requests"],
    ["/reception?condition=NOT_RECEIVED", "reception-list"],
    ["/work", "work-list"],
    ["/reports", "reports"],
  ]) {
    await page.goto(route);
    await expect(page.getByText(/Cargando/)).toHaveCount(0);
    await page.screenshot({
      path: path.join(output, file + ".png"),
      fullPage: true,
    });
  }
  await page.setViewportSize({ width: 820, height: 1180 });
  await page.goto("/requests");
  await page.getByRole("button", { name: "Abrir menú" }).click();
  await expect(
    page.getByRole("link", { name: "Administración", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: path.join(output, "tablet.png"),
    fullPage: true,
  });
});
