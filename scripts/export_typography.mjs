// Inventario reproducible de los tamaños reales y sus reglas responsive.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(path.join(root, "client/package.json"));
const css = require("postcss").parse(fs.readFileSync(path.join(root,"client/src/styles.css"),"utf8"));
const sizes = new Map();
css.walkDecls(/^--text-/, d => sizes.set(d.prop,d.value));
const rows = [];
css.walkDecls("font-size", d => {
  if (d.value === "0") return; // Hides an icon-only label; not a visible text size.
  const contexts = [];
  for (let parent=d.parent.parent;parent;parent=parent.parent) if(parent.type==="atrule") contexts.unshift(`@${parent.name} ${parent.params}`);
  const variable=d.value.match(/var\(([^)]+)\)/)?.[1];
  rows.push(`| \`${d.parent.selector.replaceAll("\n"," ")}\` | ${contexts.length ? contexts.map(x=>`\`${x}\``).join(" / ") : "General"} | \`${variable || d.value}\` | ${sizes.get(variable) || d.value} | [${d.source.start.line}](client/src/styles.css#L${d.source.start.line}) |`);
});
const section=`<!-- TYPOGRAPHY:START -->
## Dónde cambiar el tamaño de cada texto

Todos los tamaños de la web están en **client/src/styles.css**. Al principio, las variables \`--text-*\` definen la escala en **píxeles CSS**, independiente del zoom del navegador. Para cambiar un grupo completo, modifica su variable; para un texto concreto, modifica la regla del selector indicado abajo. Las reglas posteriores y los contextos responsive pueden prevalecer sobre las generales. Los textos sin tamaño explícito heredan el de su contenedor; la base es 15 px.

| Texto / componente | Control principal |
|---|---|
| Texto general, todas las páginas | \`:root\` → \`--text-body\` (15 px) |
| Títulos PageHead / ui.jsx | \`h1\`, \`.page-head\` y reglas responsive; 32 px general |
| Títulos de tarjetas / ui.jsx, detalles y formularios | \`h2\`, \`.card-title h2\`; variable según inventario |
| Campos y botones / Field, Button, SearchSelect | \`.field\`, \`.btn\`, \`.search-select\`, \`.select-popover\`; controles 14 px |
| Tablas / Dashboard, WorkPanel, ReportsPage, RequestDetail, Admin | \`th\`, \`td\`, \`.table-scroll\`, \`.table-link\`; encabezados 14 px |
| Matriz / RequestForm y AssaysEditor | \`.sample-matrix\`, \`.assay-edit-matrix\`; encabezados 14 px, datos según control |
| Estados / Badge, RequestBadges | \`.badge\`, \`.status-stack\` |
| Navegación y usuario / App.jsx | \`.workspace-nav a\`, \`.user-block\`, reglas móvil |
| LABORATORIO LURÍN / App.jsx | \`.portal-header .brand span\` → \`--text-brand\` (11 px) |
| Pie izquierdo y derecho / App.jsx | \`.workspace-footer\`, \`.workspace footer\` → \`--text-tiny\` (12 px) |
| Indicadores y gráficos / Dashboard.jsx | \`.metric-value\`, barras y leyendas: inventario de reglas debajo |
| Inicio de sesión / Login.jsx | selectores \`.login-*\` y sus excepciones responsive |
| Carga y errores / ui.jsx | \`.loading-state\`, \`.error-box\` → 14 px |

Escala central: ${[...sizes].map(([name,value])=>name + " = " + value).join("; ")}.

### Inventario exacto de declaraciones (en orden del archivo)

| Selector | Contexto | Variable | Tamaño | Línea CSS |
|---|---|---|---|---|
${rows.join("\n")}

Regenerar este inventario después de cambiar CSS: \`node scripts/export_typography.mjs\` (requiere las dependencias instaladas de client). Las fuentes del PDF son independientes: \`api/services/documents.py\`, función \`render_labels\`; no se cambian con el CSS web.
<!-- TYPOGRAPHY:END -->`;
const file=path.join(root,"README.md");
let readme=fs.readFileSync(file,"utf8");
readme=readme.includes("<!-- TYPOGRAPHY:START -->") ? readme.replace(/<!-- TYPOGRAPHY:START -->[\s\S]*?<!-- TYPOGRAPHY:END -->/,section) : readme+"\n"+section+"\n";
fs.writeFileSync(file,readme);
console.log(`Inventario tipográfico: ${rows.length} reglas.`);
