import { test, expect } from "@playwright/test";
import { randomBytes } from "node:crypto";
test.skip(
  !process.env.LAB_E2E_PASSWORD,
  "Configura una cuenta ficticia ADMIN.",
);
test("administrador crea usuario y restablece su contraseña en la plataforma", async ({
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
  await page.getByRole("link", { name: "Administración", exact: true }).click();
  await page
    .getByRole("button", { name: "Crear usuario", exact: true })
    .click();
  const modal = page.getByRole("dialog"),
    email = "qa-" + Date.now() + "@example.com",
    password = randomBytes(24).toString("base64url");
  await modal.getByLabel("Nombre", { exact: true }).fill("Cuenta ficticia QA");
  await modal.getByLabel("Correo electrónico").fill(email);
  await modal.getByLabel("Contraseña (mínimo 15 caracteres)").fill(password);
  await modal.getByLabel("Empresa", { exact: true }).selectOption({ index: 1 });
  await modal
    .getByRole("button", { name: "Crear usuario", exact: true })
    .click();
  await expect(modal).toHaveCount(0);
  const row = page.getByRole("row").filter({ hasText: email });
  await row.getByRole("button", { name: "Restablecer contraseña" }).click();
  await expect(
    page.getByRole("heading", { name: "Restablecer contraseña", exact: true }),
  ).toBeVisible();
  const next = randomBytes(24).toString("base64url");
  await page.getByLabel("Contraseña (mínimo 15 caracteres)").fill(next);
  await page.getByLabel("Repetir contraseña").fill(next);
  await page.getByRole("button", { name: "Guardar", exact: true }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page
    .getByRole("button", { name: "Cerrar sesión", exact: true })
    .click();
  await page.getByLabel("Correo electrónico").fill(email);
  await page.getByLabel("Contraseña", { exact: true }).fill(next);
  await page.getByRole("button", { name: "Ingresar", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Hola, Cuenta" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Cerrar sesión", exact: true })
    .click();
});

test("proyecto con cuatro campos y selección inicial editable", async ({
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
  await page.getByRole("link", { name: "Administración", exact: true }).click();
  await page.getByRole("button", { name: "Proyectos", exact: true }).click();
  await page
    .getByRole("button", { name: "Agregar registro", exact: true })
    .click();
  const modal = page.getByRole("dialog"),
    code = "QA-" + Date.now();
  await modal
    .getByLabel("Nombre", { exact: true })
    .fill("Proyecto de revisión de producción");
  await modal.getByLabel("Empresa", { exact: true }).selectOption({ index: 1 });
  await modal.getByLabel("Código", { exact: true }).fill(code);
  await modal.getByLabel("Ubicación", { exact: true }).fill("Lurín");
  await modal.getByRole("button", { name: "Guardar", exact: true }).click();
  await expect(modal).toHaveCount(0);
  await expect(page.getByRole("row").filter({ hasText: code })).toBeVisible();
  await page.getByRole("button", { name: "Usuarios", exact: true }).click();
  await page
    .getByRole("button", { name: "Crear usuario", exact: true })
    .click();
  await modal.getByLabel("Empresa", { exact: true }).selectOption({ index: 1 });
  await expect(modal.getByLabel(code, { exact: true })).toBeChecked();
  await modal.getByLabel(code, { exact: true }).uncheck();
  await expect(modal.getByLabel(code, { exact: true })).not.toBeChecked();
  await page.screenshot({
    path: "test-results/admin-projects-release.png",
    fullPage: true,
  });
});
