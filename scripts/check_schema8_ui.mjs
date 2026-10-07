import { chromium } from "../client/node_modules/playwright/index.mjs";
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";
const root = path.resolve(import.meta.dirname, ".."),
  output = path.join(root, ".local/review-v8");
fs.mkdirSync(output, { recursive: true });
const url = "http://127.0.0.1:5177";
const server = spawn(
  process.execPath,
  [
    path.join(root, "client/node_modules/vite/bin/vite.js"),
    "--host",
    "127.0.0.1",
    "--port",
    "5177",
    "--strictPort",
  ],
  { cwd: path.join(root, "client"), windowsHide: true, stdio: "ignore" },
);
// Catálogo de prueba desde el SQL público; nunca consulta PostgreSQL ni Azure.
const catalog = fs
  .readFileSync(path.join(root, "sql/02_catalog.sql"), "utf8")
  .split("\n")
  .filter((line) => line.startsWith("('LC-"))
  .map((line, index) => {
    const values = [...line.matchAll(/'((?:[^']|'')*)'/g)].map((m) =>
      m[1].replaceAll("''", "'"),
    );
    return {
      id: "ficticio-" + index,
      code: values[0],
      name: values[1],
      method: values[2],
      category: values[3],
      price: Number(line.match(/,([0-9.]+),true\)/)[1]),
      active: true,
    };
  });
const org = {
  id: "o1",
  name: "Lara Consulting",
  tax_id: "DEMO",
  active: true,
  is_internal: true,
};
const user = {
  id: "u1",
  name: "Persona de prueba con nombre completo",
  email: "ficticio@example.com",
  organization_id: "o1",
  organization_name: org.name,
  roles: ["ADMIN", "MANAGER"],
  active: true,
  is_internal: false,
};
let role = user,
  saved = null,
  edited = null,
  browser;
const failures = [];
const dash = {
  personal: false,
  totals: { open: 4, overdue: 1, unassigned: 2, pending_samples: 3 },
  by_type: [],
  by_technician: [],
  weekly: [],
  upcoming: [],
  economics: {
    currency: "USD",
    price_basis: "current_catalog",
    totals: {
      completed_total: 12500,
      completed_month: 2500,
      projected_total: 3500,
    },
    monthly: Array.from({ length: 12 }, (_, i) => ({
      month: `2026-${String(i + 1).padStart(2, "0")}-01`,
      amount: (i + 1) * 100,
    })),
    by_type: catalog
      .slice(0, 12)
      .map((a, i) => ({ id: a.id, name: a.name, amount: (i + 1) * 100 })),
    by_organization: [{ id: "o1", name: org.name, amount: 12500 }],
  },
};
const request = {
  id: "ficticia",
  code: "SOL-TEST",
  project_id: "EXTERNO",
  project: { code: "EXTERNO", organization_name: org.name },
  organization_name: org.name,
  status: "DRAFT",
  request_status: "CREATED",
  version: 1,
  can_edit: true,
  is_internal: false,
  district: "Lurin",
  province: "Lima",
  department: "Lima",
  samples: [],
  tasks: [],
  reports: [],
  activity: [],
  assay_counts: {},
  task_count: 0,
  completed_count: 0,
};
try {
  for (let i = 0; i < 60; i++) {
    try {
      if ((await fetch(url)).ok) break;
    } catch {}
    await new Promise((r) => setTimeout(r, 200));
  }
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const page = await browser.newPage({
    viewport: { width: 1560, height: 1100 },
  });
  page.on("pageerror", (e) => failures.push(e.message));
  await page.route("**/api/**", async (route) => {
    const p = new URL(route.request().url()).pathname,
      method = route.request().method();
    let data = [];
    if (p === "/api/session") data = { csrf: "ficticio", user: role };
    if (p === "/api/catalog") data = catalog;
    if (p === "/api/dashboard")
      data = role.roles.includes("TECH")
        ? { ...dash, personal: true, economics: undefined }
        : dash;
    if (p === "/api/management/data")
      data = {
        users: [
          user,
          {
            ...user,
            id: "u2",
            name: "Otro usuario",
            roles: ["CLIENT"],
            active: false,
          },
        ],
        organizations: [org],
        catalog,
      };
    if (p.startsWith("/api/management/catalog/") && method === "PUT") {
      edited = { id: p.split("/").at(-1), ...route.request().postDataJSON() };
      data = { ok: true };
    }
    if (p === "/api/requests" && method === "POST") {
      saved = route.request().postDataJSON();
      data = { ...request, samples: saved.samples };
    }
    if (p === "/api/requests" && method === "GET")
      data = { items: [], total: 0, page: 1, limit: 30 };
    if (p === "/api/requests/ficticia")
      data = {
        ...request,
        ...saved,
        samples: (saved?.samples || []).map((s, i) => ({
          ...s,
          id: `s${i}`,
          condition: "NOT_RECEIVED",
        })),
      };
    if (p === "/api/filter-options")
      data = { items: [], total: 0, page: 1, limit: 30 };
    await route.fulfill({ json: data });
  });
  await page.goto(url + "/admin?tab=catalog");
  await page.getByRole("columnheader", { name: "Precio (USD)" }).waitFor();
  assert.equal(await page.locator("tbody tr").count(), 58);
  await page.getByLabel("Buscar por nombre").fill("Shelby");
  await page.waitForFunction(
    () => document.querySelectorAll("tbody tr").length === 1,
  );
  assert.equal(await page.locator("tbody tr").count(), 1);
  await page.getByRole("button", { name: "Editar", exact: true }).click();
  await page.getByLabel("Código *").fill("LC-EDITADO");
  await page.getByLabel("Precio (USD) *").fill("35.50");
  await page.getByRole("button", { name: "Guardar registro" }).click();
  await page.waitForFunction(() => !document.querySelector('[role="dialog"]'));
  assert.equal(edited.id, catalog[53].id);
  assert.equal(edited.code, "LC-EDITADO");
  await page.getByRole("button", { name: "Borrar filtros" }).click();
  await page.screenshot({
    path: path.join(output, "catalog-desktop.png"),
    fullPage: true,
  });
  await page.goto(url + "/");
  await page
    .getByRole("heading", { name: "Ingresos estimados (USD)" })
    .waitFor();
  await page.getByRole("button", { name: "Ver todos", exact: true }).click();
  await page.screenshot({
    path: path.join(output, "income-desktop.png"),
    fullPage: true,
  });
  role = { ...user, roles: ["CLIENT"], is_internal: false };
  await page.goto(url + "/requests/new");
  await page.getByLabel("Distrito *", { exact: true }).fill("Lurin");
  await page.getByLabel("Provincia *", { exact: true }).fill("Lima");
  await page.getByLabel("Departamento *", { exact: true }).fill("Lima");
  assert.equal(await page.getByLabel("Nombre de la solicitud *").count(), 0);
  assert.equal(await page.getByLabel("Coordenadas Este").count(), 0);
  await page
    .getByLabel("Fecha estimada arribo muestra (opcional)")
    .fill("2026-11-01");
  await page.screenshot({
    path: path.join(output, "request-dates.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Continuar con las muestras" })
    .click();
  await page.getByRole("button", { name: "Pegar Excel" }).click();
  await page
    .getByPlaceholder("Celdas separadas por tabulaciones")
    .fill(
      Array.from(
        { length: 30 },
        (_, i) =>
          `C-${i}\tM${i + 1}\t5.12345\t6\tSuelo\t2\t1.2\tNotas de muestra\t123456.7\t8765432.1`,
      ).join("\n"),
    );
  await page.getByRole("button", { name: "Incorporar filas" }).click();
  assert.equal(await page.locator(".sample-matrix tbody tr").count(), 30);
  assert.equal(
    await page
      .getByLabel("Prof. inicial (m) · fila 1", { exact: true })
      .inputValue(),
    "5.12",
  );
  await page.getByLabel("Prof. inicial (m) · fila 1", { exact: true }).focus();
  assert.equal(
    await page
      .getByLabel("Prof. inicial (m) · fila 1", { exact: true })
      .inputValue(),
    "5.12345",
  );
  await page.getByLabel("Seleccionar todas las filas").check();
  await page
    .getByRole("button", { name: "Añadir ensayos a 30 muestras seleccionadas" })
    .click();
  await page.getByLabel("Buscar ensayo", { exact: true }).fill("SHELBY");
  await page
    .locator(".assay-option")
    .filter({ hasText: "Apertura de Tubo Shelby" })
    .getByRole("checkbox")
    .check();
  await page.getByLabel("Buscar ensayo", { exact: true }).fill("UCS");
  await page.locator(".assay-option").first().getByRole("checkbox").check();
  await page.screenshot({
    path: path.join(output, "assay-picker-desktop.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Añadir seleccionados" }).click();
  assert.equal(await page.locator(".selected-assay").count(), 60);
  assert.equal(await page.locator(".sample-matrix th").count(), 13);
  assert.equal(await page.locator(".sample-matrix tfoot td").count(), 1);
  await page.screenshot({
    path: path.join(output, "sample-matrix-desktop.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Revisar solicitud" }).click();
  await page.getByRole("button", { name: "Guardar borrador" }).click();
  await page.waitForURL("**/requests/ficticia");
  assert(!("title" in saved) && !("easting" in saved));
  assert.equal(saved.samples[0].depth_from, "5.12345");
  assert.equal(saved.samples[0].weight, "1.2");
  assert.equal(saved.samples[0].easting, 123456.7);
  assert(saved.samples.every((s) => s.assay_ids.length === 2));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(url + "/requests/new");
  await page
    .getByRole("heading", { name: "Datos del servicio", exact: true })
    .waitFor();
  await page.screenshot({
    path: path.join(output, "request-mobile.png"),
    fullPage: true,
  });
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  );
  role = user;
  await page.goto(url + "/admin?tab=catalog");
  await page.getByRole("columnheader", { name: "Precio (USD)" }).waitFor();
  await page.screenshot({
    path: path.join(output, "catalog-mobile.png"),
    fullPage: true,
  });
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  );
  await page.goto(url + "/");
  await page
    .getByRole("heading", { name: "Ingresos estimados (USD)" })
    .waitFor();
  await page.screenshot({
    path: path.join(output, "income-mobile.png"),
    fullPage: true,
  });
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  );
  assert.deepEqual(failures, []);
  console.log(
    "Chrome: filtros, edición por ID, importación 30 muestras, selector/bulk, coordenadas, precisión, formulario sin título y desktop/móvil verificados.",
  );
} finally {
  await browser?.close();
  server.kill();
}
