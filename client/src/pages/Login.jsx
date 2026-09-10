import { useState } from "react";
import { FlaskConical } from "lucide-react";
import { api, messageOf } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { Button, Field, ErrorBox } from "../components/ui";
export default function Login() {
  const { accept } = useAuth();
  const [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const { data } = await api.post("/auth/login", { email, password });
      accept(data);
      setPassword("");
    } catch (e) {
      setError(messageOf(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="login-page">
      <section className="login-story">
        <img src="/logo.png" alt="Lara Consulting" />
        <span className="eyebrow">LABORATORIO LURÍN</span>
        <h1>
          Cada muestra.
          <br />
          Cada ensayo.
          <br />
          Todo conectado.
        </h1>
        <p>
          Gestiona tus solicitudes y consulta el avance de tus estudios de
          suelos y relaves.
        </p>
        <FlaskConical size={130} strokeWidth={1} />
      </section>
      <section className="login-panel">
        <form onSubmit={submit} className="login-form">
          <h2>Bienvenido al laboratorio</h2>
          <p className="muted">
            Ingresa con la cuenta que te asignó el administrador.
          </p>
          <ErrorBox>{error}</ErrorBox>
          <Field label="Correo electrónico">
            <input
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </Field>
          <Field label="Contraseña">
            <input
              type="password"
              autoComplete="current-password"
              required
              maxLength={128}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </Field>
          <Button variant="primary full" busy={busy}>
            Ingresar
          </Button>
          <p className="muted section-gap">
            Para crear una cuenta o restablecer tu contraseña, contacta al
            administrador.
          </p>
        </form>
      </section>
    </div>
  );
}
