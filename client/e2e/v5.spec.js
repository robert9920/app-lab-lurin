import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
const output = path.resolve("../.local/review-v5");
test.skip(
  !process.env.LAB_E2E_PASSWORD,
  "Requiere base ficticia con esquema 6.",
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
async function write(page, method, route, data) {
  const session = await (await page.request.get("/api/session")).json();
  const result = await page.request.fetch("/api" + route, {
    method,
    data,
    headers: {
      Origin: new URL(page.url()).origin,
      "X-CSRF-Token": session.csrf,
    },
  });
  expect(result.ok(), await result.text()).toBeTruthy();
  return result.json();
}
test("cliente externo: carga, formulario compacto y coordenadas", async ({
  page,
}) => {
  await login(page, "externo@example.com");
  await page.route("**/api/requests?**", async (route) => {
    await new Promise((r) => setTimeout(r, 600));
    await route.continue();
  });
  await page.goto("/requests");
  await expect(
    page.getByText("Cargando solicitudes…", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("combobox", { name: "Proyecto", exact: true }),
  ).toHaveCount(0);
  await expect(page.getByLabel("Creada desde")).toBeVisible();
  await page.getByRole("link", { name: "Nueva solicitud" }).click();
  await expect(
    page.locator(".service-heading .external-service"),
  ).toBeVisible();
  await page.getByLabel("Nombre de la solicitud").fill("Coordenadas externas");
  for (const field of ["Distrito", "Provincia", "Departamento"])
    await page.getByLabel(field + " *", { exact: true }).fill("Lima");
  await page.getByLabel("Coordenadas Este (opcional)").fill("12345");
  await page
    .getByRole("button", { name: "Continuar con las muestras" })
    .click();
  await expect(page.getByRole("alert")).toContainText("6");
  await page.getByLabel("Coordenadas Este (opcional)").fill("123456.25");
  await expect(page.locator(".network-loading")).toHaveCount(0);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: path.join(output, "external-form.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Continuar con las muestras" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Muestras y ensayos" }),
  ).toBeVisible();
});
test("cuatro listas: solicitante, filtros buscables, estados múltiples y vacío", async ({
  page,
}) => {
  await login(page, "jefe@example.com");
  for (const route of ["requests", "reception", "work", "reports"]) {
    await page.goto("/" + route);
    const people = page.getByRole("combobox", {
      name: "Solicitante",
      exact: true,
    });
    await people.fill("ana");
    await expect(page.locator(".select-popover")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(
      page.getByRole("combobox", { name: "Empresa", exact: true }),
    ).toBeVisible();
    await expect(page.locator(".loading-state")).toHaveCount(0);
    await page.screenshot({
      path: path.join(output, route + ".png"),
      fullPage: true,
    });
  }
  await page.goto("/requests");
  const requester = page.getByRole("combobox", {
    name: "Solicitante",
    exact: true,
  });
  await requester.fill("dIEgO");
  await expect(page.getByRole("option", { name: /Diego/ })).toBeVisible();
  await requester.press("Enter");
  await expect(page).toHaveURL(/requester=/);
  await page.reload();
  await expect(requester).toHaveValue(/Diego/);
  await page
    .getByRole("button", { name: "Limpiar selección", exact: true })
    .click();
  const state = page.getByRole("combobox", { name: "Estado", exact: true });
  await state.click();
  await page.getByRole("option", { name: /Aprobado/ }).click();
  await page.getByRole("option", { name: /En revisión/ }).click();
  await page.keyboard.press("Escape");
  await expect(page).toHaveURL(/status=.*APPROVED.*SUBMITTED/);
  await page.reload();
  await expect(state).toHaveValue(/Aprobado/);
  await expect(state).toHaveValue(/En revisión/);
  await page
    .getByLabel("Buscar solicitud", { exact: true })
    .fill("SIN_COINCIDENCIA_938438");
  await expect(
    page.getByText("No hay solicitudes con estos filtros."),
  ).toBeVisible();
  await page.screenshot({
    path: path.join(output, "empty.png"),
    fullPage: true,
  });
});

test("panel de acciones solo al seleccionar y distribución en tablet", async ({
  page,
}) => {
  await login(page, "jefe@example.com");
  await page.goto("/work");
  await expect(page.locator(".work-layout.no-actions")).toBeVisible();
  await page.locator('tbody input[type="checkbox"]:enabled').first().check();
  await expect(page.getByLabel("Acción", { exact: true })).toBeVisible();
  await expect(page.locator(".work-layout.no-actions")).toHaveCount(0);
  await page.screenshot({
    path: path.join(output, "work-selected.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 1024, height: 900 });
  await page.screenshot({
    path: path.join(output, "work-tablet.png"),
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.setViewportSize({ width: 768, height: 900 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
});
test("aprobación parcial y edición posterior desde la interfaz", async ({
  page,
  browser,
}) => {
  await login(page, "externo@example.com");
  const catalog = await (await page.request.get("/api/catalog")).json();
  const aid = catalog.find((a) => a.code === "HUM").id;
  let r = await write(page, "POST", "/requests", {
    title: "Prueba visual parcial " + Date.now(),
    district: "Lurín",
    province: "Lima",
    department: "Lima",
    samples: [
      { client_code: "VIS-1", material: "Suelo", assay_ids: [aid] },
      { client_code: "VIS-2", material: "Relaves", assay_ids: [] },
    ],
  });
  r = await write(page, "POST", `/requests/${r.id}/actions`, {
    version: r.version,
    action: "submit",
  });
  const manager = await browser.newPage({
    baseURL: process.env.LAB_E2E_URL || "http://localhost:5173",
    viewport: { width: 1440, height: 1000 },
  });
  await login(manager, "jefe@example.com");
  await manager.goto(`/requests/${r.id}`);
  await manager.getByRole("button", { name: "Revisar ensayos (1)" }).click();
  await manager.getByLabel(/Decisión ·/).selectOption("APPROVED");
  await manager.getByRole("button", { name: "Guardar decisiones (1)" }).click();
  await expect(
    manager.getByText("Ensayos pendientes de definir", { exact: true }),
  ).toBeVisible();
  await page.goto(`/requests/${r.id}`);
  await page
    .getByRole("link", { name: "Solicitar ensayos", exact: true })
    .click();
  const assayName = catalog.find((a) => a.id === aid).name;
  await expect(
    page.getByRole("checkbox", { name: assayName + " · VIS-1", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("checkbox", { name: assayName + " · VIS-2", exact: true })
    .check();
  await page.screenshot({
    path: path.join(output, "complete-assays.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Guardar ensayos para revisión" })
    .click();
  await expect(page.getByText("1 por aprobar", { exact: true })).toBeVisible();
  await manager.reload();
  await manager.getByRole("button", { name: "Revisar ensayos (1)" }).click();
  await manager.getByLabel(/Decisión ·/).selectOption("APPROVED");
  await manager.getByRole("button", { name: "Guardar decisiones (1)" }).click();
  await expect(manager.getByText("1 por aprobar", { exact: true })).toHaveCount(
    0,
  );
  await page.goto(`/requests/${r.id}?tab=work`);
  await expect(page.locator(".work-layout.no-actions")).toBeVisible();
  await page.screenshot({
    path: path.join(output, "client-assays.png"),
    fullPage: true,
  });
  await page.evaluate(() => {
    document.body.style.zoom = "0.8";
  });
  await page.screenshot({
    path: path.join(output, "client-assays-80.png"),
    fullPage: true,
  });
  await manager.close();
});
