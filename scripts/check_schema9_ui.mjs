// UI con respuestas ficticias: no conecta PostgreSQL ni Azure, no usa cuentas reales.
import { chromium } from "../client/node_modules/@playwright/test/index.mjs";
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";

const root = path.resolve(import.meta.dirname, ".."),
  output = path.join(root, ".local/review-v9");
fs.mkdirSync(output, { recursive: true });
const url = "http://127.0.0.1:5178";
const server = spawn(
  process.execPath,
  [
    path.join(root, "client/node_modules/vite/bin/vite.js"),
    "--host",
    "127.0.0.1",
    "--port",
    "5178",
    "--strictPort",
  ],
  { cwd: path.join(root, "client"), windowsHide: true, stdio: "ignore" },
);
const user = {
  id: "u1",
  name: "Cliente ficticio",
  organization_name: "Compañía Perú",
  roles: ["CLIENT"],
  is_internal: false,
};
let role = user,
  lastPayload,
  serial = 0,
  browser;
const records = new Map(),
  failures = [];
const sample = {
  id: "s1",
  client_code: "M-01",
  borehole: "DH-01",
  material: "Suelo",
  condition: "OK",
  notes: "Comentario de muestra\nDetalle adicional",
  assay_ids: [],
};
const record = {
  id: "visible",
  code: "SOL-TEST-001",
  project_id: "EXTERNO",
  project_code: "EXTERNO",
  project: { code: "EXTERNO", organization_name: "Compañía Perú" },
  status: "APPROVED",
  request_status: "CREATED",
  notes:
    "Indicaciones extensas de prueba\nConservar el material protegido durante su recepción y preparación.",
  version: 1,
  can_cancel: true,
  can_edit: false,
  samples: [sample],
  tasks: [],
  reports: [],
  activity: [],
  assay_counts: {},
  created_at: "2026-10-07T13:00:00Z",
  requester_name: "Cliente ficticio",
  organization_name: "Compañía Perú",
};
records.set(record.id, record);
records.set("draft", {
  ...record,
  id: "draft",
  code: "SOL-DRAFT",
  status: "DRAFT",
  can_cancel: false,
  can_edit: true,
});
const tasks = ["OBSERVED", "CANCELLED"].map((state, i) => ({
  id: "t" + i,
  sample_id: sample.id,
  sample_code: sample.client_code,
  assay_name: "Ensayo de prueba " + i,
  approved: true,
  review_status: "APPROVED",
  state,
  state_reason: i
    ? "Cancelación de prueba\nMotivo extenso para revisar su ajuste"
    : "Observación de prueba\nCorregir la preparación",
  state_reason_author: "Jefatura",
  state_reason_at: "2026-10-07T12:00:00Z",
  condition: "OK",
  allowed_actions: [],
  technician_name: "Lucía Torres",
}));
record.tasks = tasks;

try {
  for (let i = 0; i < 60; i++) {
    try {
      if ((await fetch(url)).ok) break;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const page = await browser.newPage({
    viewport: { width: 1600, height: 1000 },
  });
  page.on("pageerror", (error) => failures.push(error.message));
  await page.route("**/api/**", async (route) => {
    const p = new URL(route.request().url()).pathname,
      method = route.request().method();
    let data = [];
    if (p === "/api/session") data = { csrf: "fake", user: role };
    if (p === "/api/catalog") data = [];
    if (p === "/api/requests" && method === "GET")
      data = {
        items: [...records.values()],
        total: records.size,
        page: 1,
        limit: 30,
      };
    if (p === "/api/requests" && method === "POST") {
      lastPayload = route.request().postDataJSON();
      const id = "saved" + ++serial;
      data = {
        ...record,
        ...lastPayload,
        id,
        code: "SOL-SAVED-" + serial,
        status: "DRAFT",
        request_status: "CREATED",
        can_cancel: false,
        can_edit: true,
        tasks: [],
        samples: lastPayload.samples.map((s, i) => ({
          ...s,
          id: "saved-s" + i,
          condition: "NOT_RECEIVED",
        })),
      };
      records.set(id, data);
    }
    if (/^\/api\/requests\/[^/]+$/.test(p))
      data = records.get(p.split("/").at(-1));
    if (p === "/api/filter-options")
      data = { items: [], total: 0, page: 1, limit: 30 };
    if (p === "/api/management/data")
      data = {
        users: [
          { ...user, name: "Lucía Torres", roles: ["TECH"], active: true },
        ],
        organizations: [
          {
            id: "org",
            name: "Compañía Perú",
            active: true,
            is_internal: false,
          },
        ],
        catalog: [
          {
            id: "a1",
            code: "LC-001",
            name: "Análisis Granulométrico",
            method: "Método de prueba",
            category: "Caracterización",
            price: 11,
            active: true,
          },
        ],
      };
    await route.fulfill({ json: data });
  });
  // Guardado desde paso1 sin datos obligatorios ni muestras.
  await page.goto(url + "/requests/new");
  await page
    .getByRole("button", { name: "Guardar borrador", exact: true })
    .waitFor();
  await page
    .getByLabel("Indicaciones generales (opcional)")
    .fill("Primer progreso");
  await page
    .getByRole("button", { name: "Guardar borrador", exact: true })
    .click();
  await page.waitForURL("**/requests/saved1");
  await page.locator(".status-stack .badge-DRAFT").waitFor();
  assert.equal(lastPayload.samples.length, 0);
  assert.equal(lastPayload.notes, "Primer progreso");
  assert.equal(
    await page.getByRole("button", { name: "Cancelar solicitud" }).count(),
    0,
  );
  assert.equal(await page.locator(".status-stack .badge-DRAFT").count(), 1);
  // Paso2: fila parcial sin código ni tipo.
  await page.goto(url + "/requests/new");
  await page.getByLabel("Distrito *", { exact: true }).fill("Lurín");
  await page.getByLabel("Provincia *", { exact: true }).fill("Lima");
  await page.getByLabel("Departamento *", { exact: true }).fill("Lima");
  await page
    .getByRole("button", { name: "Continuar con las muestras" })
    .click();
  await page
    .getByLabel("Calicata / sondaje · fila 1", { exact: true })
    .fill("DH-01");
  await page
    .getByRole("button", { name: "Guardar borrador", exact: true })
    .click();
  await page.waitForURL("**/requests/saved2");
  assert.equal(lastPayload.samples.length, 1);
  assert.equal(lastPayload.samples[0].borehole, "DH-01");
  // Paso3 conserva guardado existente.
  await page.goto(url + "/requests/new");
  for (const field of ["Distrito *", "Provincia *", "Departamento *"])
    await page.getByLabel(field, { exact: true }).fill("Lima");
  await page
    .getByRole("button", { name: "Continuar con las muestras" })
    .click();
  await page.getByLabel("Muestra * · fila 1", { exact: true }).fill("M-01");
  await page
    .getByLabel("Tipo de muestra * · fila 1", { exact: true })
    .fill("Suelo");
  await page.getByRole("button", { name: "Revisar solicitud" }).click();
  await page
    .getByRole("button", { name: "Guardar borrador", exact: true })
    .click();
  await page.waitForURL("**/requests/saved3");
  assert.equal(lastPayload.samples[0].client_code, "M-01");
  await page.goto(url + "/requests");
  await page
    .getByRole("columnheader", { name: "Indicaciones generales" })
    .waitFor();
  assert.equal(await page.locator(".badge-DRAFT").count(), 4);
  await page.screenshot({
    path: path.join(output, "solicitudes-desktop.png"),
    fullPage: true,
  });
  await page.goto(url + "/requests/visible");
  await page
    .getByRole("columnheader", { name: "Comentarios", exact: true })
    .waitFor();
  assert.equal(await page.locator(".general-comment").count(), 1);
  assert.equal(
    await page.getByRole("cell", { name: /Comentario de muestra/ }).count(),
    1,
  );
  await page.screenshot({
    path: path.join(output, "resumen-desktop.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Ensayos", exact: true }).click();
  await page.getByText("Motivo de observación", { exact: true }).waitFor();
  await page.getByText("Motivo de cancelación", { exact: true }).waitFor();
  await page.screenshot({
    path: path.join(output, "motivos-desktop.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Resumen y muestras" }).click();
  await page.screenshot({
    path: path.join(output, "resumen-mobile.png"),
    fullPage: true,
  });
  const boxes = await page.locator(".summary-footer").evaluate((el) => {
    const note = el.querySelector(".general-comment").getBoundingClientRect(),
      action = el.querySelector(".form-actions").getBoundingClientRect();
    return { noteBottom: note.bottom, actionTop: action.top };
  });
  assert.ok(boxes.actionTop >= boxes.noteBottom);
  await page.getByRole("button", { name: "Ensayos", exact: true }).click();
  await page.getByText("Motivo de observación", { exact: true }).waitFor();
  await page.screenshot({
    path: path.join(output, "motivos-mobile.png"),
    fullPage: true,
  });
  role = { ...user, roles: ["ADMIN"] };
  await page.setViewportSize({ width: 1600, height: 1000 });
  for (const [tab, query, name] of [
    ["users", "Lucia", "Lucía Torres"],
    ["organizations", "compania peru", "Compañía Perú"],
    ["catalog", "analisis", "Análisis Granulométrico"],
  ]) {
    await page.goto(url + "/admin?tab=" + tab);
    await page.getByLabel("Buscar por nombre").fill(query);
    await page.getByRole("cell", { name, exact: false }).waitFor();
    assert.equal(await page.locator("tbody tr").count(), 1);
  }
  assert.deepEqual(failures, []);
  console.log(
    "UI: borradores en los tres pasos, etiquetas, comentarios, motivos, búsqueda sin tildes y móvil verificados.",
  );
} finally {
  if (browser) await browser.close();
  server.kill();
}
