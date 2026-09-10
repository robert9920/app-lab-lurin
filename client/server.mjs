import express from "express";
import helmet from "helmet";
import { rateLimit } from "express-rate-limit";
import { createProxyMiddleware } from "http-proxy-middleware";
import path from "node:path";
import { fileURLToPath } from "node:url";
const target = process.env.API_TARGET;
if (
  !target ||
  (process.env.NODE_ENV === "production" &&
    (!target.startsWith("https://") || !process.env.FUNCTION_PROXY_KEY))
)
  throw new Error("Configure API_TARGET and server-side FUNCTION_PROXY_KEY");
const app = express();
app.disable("x-powered-by");
app.set("trust proxy", 1);
app.use(
  helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        scriptSrc: ["'self'"],
        styleSrc: ["'self'", "'unsafe-inline'"],
        imgSrc: ["'self'", "data:"],
        connectSrc: ["'self'"],
        objectSrc: ["'none'"],
        frameAncestors: ["'none'"],
      },
    },
    referrerPolicy: { policy: "no-referrer" },
  }),
);
app.use(
  "/api/auth",
  rateLimit({
    windowMs: 15 * 60 * 1000,
    limit: 60,
    standardHeaders: "draft-8",
    legacyHeaders: false,
    message: { error: "Demasiados intentos. Espera unos minutos." },
  }),
);
app.use(
  createProxyMiddleware({
    pathFilter: "/api",
    target,
    changeOrigin: true,
    proxyTimeout: 60000,
    on: {
      proxyReq(proxyReq) {
        proxyReq.removeHeader("x-functions-key");
        proxyReq.setHeader(
          "x-functions-key",
          process.env.FUNCTION_PROXY_KEY || "",
        );
      },
      error(_err, _req, res) {
        res.writeHead(502, { "Content-Type": "application/json" });
        res.end(
          JSON.stringify({
            error: "El servicio no está disponible temporalmente.",
          }),
        );
      },
    },
  }),
);
const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "dist");
app.use(express.static(root, { index: false, maxAge: "1h" }));
app.get("/{*path}", (_req, res) => {
  res.set("Cache-Control", "no-store");
  res.sendFile(path.join(root, "index.html"));
});
app.listen(Number(process.env.PORT || 8080), "0.0.0.0");
