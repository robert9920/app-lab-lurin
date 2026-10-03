import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
const output = path.resolve("../.local/review-v6");
test.skip(
  !process.env.LAB_E2E_PASSWORD,
  "Requiere cuentas ficticias y esquema 6.",
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
  expect(result.ok()).toBeTruthy();
  return result.json();
}
async function create(page, title) {
  const catalog = await (await page.request.get("/api/catalog")).json();
  const aid = catalog.find((a) => a.code === "HUM").id;
  let r = await write(page, "POST", "/requests", {
    title,
    district: "Lurín",
    province: "Lima",
    department: "Lima",
    samples: [
      { client_code: "UI-1", material: "Suelo", assay_ids: [aid] },
      { client_code: "UI-2", material: "Relaves", assay_ids: [aid] },
    ],
  });
  return write(page, "POST", `/requests/${r.id}/actions`, {
    version: r.version,
    action: "submit",
  });
}

test("cabecera completa, avisos repetidos y pasos de sacos/peso", async ({
  page,
}) => {
  await login(page, "externo@example.com");
  const session = await (await page.request.get("/api/session")).json();
  await expect(page.locator(".user-block b")).toHaveText(session.user.name);
  await expect(page.locator(".user-block small")).toHaveText(
    session.user.organization_name,
  );
  expect(
    await page
      .locator(".user-block b")
      .evaluate((el) => getComputedStyle(el).textOverflow),
  ).toBe("clip");
  await page.goto("/requests/new");
  await page.getByLabel("Nombre de la solicitud").fill("Avisos de coordenadas");
  for (const field of ["Distrito", "Provincia", "Departamento"])
    await page.getByLabel(field + " *", { exact: true }).fill("Lima");
  await page.getByLabel("Coordenadas Norte (opcional)").fill("123");
  const next = page.getByRole("button", { name: "Continuar con las muestras" });
  await next.click();
  await expect(page.getByRole("alert")).toContainText("Coordenadas Norte");
  await page.waitForTimeout(3000);
  await next.click();
  await page.waitForTimeout(3000);
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0, { timeout: 4000 });
  await page.getByLabel("Coordenadas Norte (opcional)").fill("");
  await next.click();
  const bags = page.getByLabel("Sacos · fila 1", { exact: true }),
    weight = page.getByLabel("Peso (kg) · fila 1", { exact: true });
  await bags.press("ArrowUp");
  await expect(bags).toHaveValue("1");
  await bags.press("ArrowUp");
  await expect(bags).toHaveValue("2");
  await weight.press("ArrowUp");
  await expect(weight).toHaveValue("0.1");
  await weight.fill("0.025");
  await weight.press("ArrowUp");
  await expect(weight).toHaveValue("0.125");
  expect(await weight.evaluate((el) => el.validity.stepMismatch)).toBe(false);
  await page
    .getByRole("button", { name: "Revisar solicitud", exact: true })
    .click();
  await expect(page.locator(".cell-error").first()).toBeVisible();
  await expect(page.locator(".cell-error")).toHaveCount(0, { timeout: 7000 });
  await expect(
    page.locator('input[aria-invalid="true"]').first(),
  ).toBeVisible();
  await page.setViewportSize({ width: 768, height: 900 });
  await page.screenshot({
    path: path.join(output, "header-tablet.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator(".user-block b")).toHaveText(session.user.name);
  await expect(page.locator(".user-block small")).toHaveText(
    session.user.organization_name,
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: path.join(output, "header-mobile.png"),
    fullPage: true,
  });
});

test("Borrar filtros en las cuatro listas y fecha de creación", async ({
  page,
}) => {
  await login(page, "jefe@example.com");
  for (const route of ["requests", "reception", "work", "reports"]) {
    await page.goto("/" + route + "?page=2&project=DEMO-001");
    const project = page.getByRole("combobox", {
      name: "Proyecto",
      exact: true,
    });
    await project.fill("SIN_COINCIDENCIA");
    await page
      .getByRole("button", { name: "Borrar filtros", exact: true })
      .click();
    await expect(page).toHaveURL(new RegExp("/" + route + "$"));
    await expect(project).toHaveValue("");
    if (route === "requests") {
      await expect(
        page.getByRole("columnheader", { name: "Fecha de creación" }),
      ).toBeVisible();
      await expect(
        page.getByRole("combobox", {
          name: "Ensayos por definir",
          exact: true,
        }),
      ).toHaveCount(0);
    }
  }
  await page.screenshot({
    path: path.join(output, "reports-filters.png"),
    fullPage: true,
  });
});

test("decisiones individuales, motivo, reenvío y filtro En revisión", async ({
  page,
  browser,
}) => {
  await login(page, "externo@example.com");
  const title = "Revisión UI " + Date.now(),
    r = await create(page, title);
  const manager = await browser.newPage({
    baseURL: process.env.LAB_E2E_URL,
    viewport: { width: 1440, height: 1000 },
  });
  await login(manager, "jefe@example.com");
  await manager.goto(`/requests/${r.id}`);
  await manager.getByRole("button", { name: "Revisar ensayos (2)" }).click();
  const decisions = manager.getByRole("combobox", { name: /Decisión/ });
  await decisions.nth(0).selectOption("APPROVED");
  await decisions.nth(1).selectOption("REJECTED");
  await manager.getByRole("button", { name: "Guardar decisiones (2)" }).click();
  await expect(manager.getByRole("alert")).toContainText("motivo");
  await manager
    .getByRole("textbox", { name: /Motivo · UI-2/ })
    .fill("Confirmar el método");
  await manager.screenshot({
    path: path.join(output, "independent-review.png"),
    fullPage: true,
  });
  await manager.getByRole("button", { name: "Guardar decisiones (2)" }).click();
  await expect(manager.getByRole("dialog")).toHaveCount(0);
  await page.goto(`/requests/${r.id}?tab=work`);
  await expect(
    page.getByText("Motivo: Confirmar el método", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: path.join(output, "rejected-client.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Volver a solicitar", exact: true })
    .click();
  await expect(page.getByText("Por aprobar", { exact: true })).toHaveCount(1);
  await manager.goto(
    "/requests?status=SUBMITTED&q=" + encodeURIComponent(title),
  );
  await expect(manager.getByText(title, { exact: true })).toBeVisible();
  await manager.goto(`/requests/${r.id}`);
  await manager.getByRole("button", { name: "Revisar ensayos (1)" }).click();
  await manager
    .getByRole("combobox", { name: /Decisión/ })
    .selectOption("APPROVED");
  await manager.getByRole("button", { name: "Guardar decisiones (1)" }).click();
  await page.reload();
  await expect(page.getByText("Por aprobar", { exact: true })).toHaveCount(0);
  await manager.close();
});

test("fallo de consulta: el aviso desaparece sin reactivar carga", async ({
  page,
}) => {
  await login(page, "jefe@example.com");
  await page.route("**/api/dashboard", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ error: "Consulta no disponible" }),
    }),
  );
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText("Consulta no disponible");
  await expect(page.getByRole("alert")).toHaveCount(0, { timeout: 7000 });
  await expect(
    page.getByText("Cargando indicadores…", { exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Reintentar consulta" }),
  ).toBeVisible();
});
