import { test, expect } from "@playwright/test";
import path from "node:path";
import fs from "node:fs";

const out = path.resolve("../.local/review");
test.beforeAll(() => fs.mkdirSync(out, { recursive: true }));
async function login(page, email, password) {
  await page.goto("/");
  await page.getByLabel("Correo electrónico").fill(email);
  await page.getByLabel("Contraseña", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Ingresar", exact: true }).click();
}

test("cliente: contraste y ficha sin indicaciones vacías", async ({ page }) => {
  test.skip(!process.env.LAB_E2E_CLIENT_PASSWORD, "Requiere cliente ficticio.");
  await login(page, "cliente@example.com", process.env.LAB_E2E_CLIENT_PASSWORD);
  const link = page.getByRole("link", { name: "Ver solicitudes", exact: true });
  await expect(link).toBeVisible();
  const contrast = await link.evaluate((el) => {
    const css = getComputedStyle(el);
    const lum = (rgb) => rgb.match(/[\d.]+/g).slice(0, 3).map(Number).map((c) => c / 255).map((c) => c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4).reduce((n, v, i) => n + v * [.2126,.7152,.0722][i], 0);
    const a = lum(css.color), b = lum(css.backgroundColor);
    return (Math.max(a,b) + .05) / (Math.min(a,b) + .05);
  });
  expect(contrast).toBeGreaterThanOrEqual(4.5);
  await page.screenshot({ path: path.join(out, "client-v3.png"), fullPage: true });
  await link.click();
  await page.getByLabel("Buscar solicitud").fill("SOL-DEMO-002");
  await page.getByRole("link", { name: "Abrir", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Solicitud y muestras", exact: true })).toBeVisible();
  await expect(page.getByText("Sin indicaciones adicionales.", { exact: true })).toHaveCount(0);
  await page.screenshot({ path: path.join(out, "summary-v3.png"), fullPage: true });
});

test("técnico: dashboard propio, acciones válidas y etiquetas seleccionadas", async ({ page }) => {
  test.skip(!process.env.LAB_E2E_TECH_PASSWORD, "Requiere técnico ficticio.");
  await login(page, "tecnico@example.com", process.env.LAB_E2E_TECH_PASSWORD);
  await expect(page.getByRole("heading", { name: "Mi carga de trabajo", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Estado de mis ensayos abiertos" })).toBeVisible();
  await page.screenshot({ path: path.join(out, "technician-v3.png"), fullPage: true });
  await page.getByRole("link", { name: "Trabajo de laboratorio", exact: true }).click();
  await expect(page.getByLabel("Técnico", { exact: true })).toHaveCount(0);
  await page.getByLabel("Estado", { exact: true }).selectOption("PENDING");
  await expect(page.getByText("ficha de ensayos", { exact: false })).toHaveCount(0);
  await page.getByRole("checkbox", { name: "Seleccionar todos", exact: true }).check();
  await expect(page.getByLabel("Acción").getByRole("option")).toHaveText(["Iniciar"]);
  await page.getByLabel("Estado", { exact: true }).selectOption("RUNNING");
  await expect(page.getByRole("cell", { name: "En ejecución", exact: true })).toBeVisible();
  await page.getByRole("checkbox", { name: "Seleccionar todos", exact: true }).check();
  await expect(page.getByLabel("Acción").getByRole("option")).toHaveText(["Observar", "Completar"]);
  await page.screenshot({ path: path.join(out, "actions-v3.png"), fullPage: true });
  await page.getByRole("link", { name: "Recepción", exact: true }).click();
  await page.getByRole("link", { name: "Registrar recepción", exact: true }).click();
  await page.getByRole("checkbox", { name: "Todas las muestras recibidas", exact: true }).check();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Imprimir etiquetas", exact: true }).click();
  await (await download).saveAs(path.join(out, "labels-v3.pdf"));
  await page.getByRole("button", { name: "Historial", exact: true }).click();
  await expect(page.getByText("Ver detalle del cambio", { exact: true })).toHaveCount(0);
});
