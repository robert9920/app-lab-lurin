import { useState } from "react";
import {
  NavLink,
  Routes,
  Route,
  Navigate,
  useLocation,
} from "react-router-dom";
import {
  LayoutDashboard,
  ClipboardList,
  PackageCheck,
  FlaskConical,
  FileText,
  Settings,
  LogOut,
  Menu,
  ShieldCheck,
} from "lucide-react";
import { useAuth } from "./context/AuthContext";
import Login from "./pages/Login";
import Dashboard, { RequestList } from "./pages/Dashboard";
import RequestDetail from "./pages/RequestDetail";
import RequestForm from "./pages/RequestForm";
import Admin from "./pages/Admin";
import WorkPage from "./pages/WorkPage";
import ReportsPage from "./pages/ReportsPage";
import { labels } from "./components/ui";
export default function App() {
  const { user, loading, logout } = useAuth(),
    [open, setOpen] = useState(false),
    location = useLocation();
  if (loading)
    return (
      <div className="center-page">
        <FlaskConical className="spin" /> Cargando laboratorio…
      </div>
    );
  if (!user) return <Login />;
  const staff = user.roles.some((r) =>
    ["ADMIN", "MANAGER", "TECH"].includes(r),
  );
  const canRequest = user.roles.includes("CLIENT");
  const navigation = [
    ["/", "Inicio", LayoutDashboard],
    ["/requests", "Solicitudes", ClipboardList],
    ...(staff
      ? [
          ["/reception", "Recepción", PackageCheck],
          ["/work", "Trabajo de laboratorio", FlaskConical],
        ]
      : []),
    ["/reports", "Informes", FileText],
    ...(user.roles.includes("ADMIN")
      ? [["/admin", "Administración", Settings]]
      : []),
  ];
  return (
    <div className="app-shell">
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <a href="/" className="brand">
          <img src="/logo.png" alt="Lara Consulting" />
          <span>LABORATORIO LURÍN</span>
        </a>
        <div className="nav-caption">ESPACIO DE TRABAJO</div>
        <nav>
          {navigation.map(([to, title, Icon]) => (
            <NavLink
              className={({ isActive }) =>
                (
                  location.pathname.startsWith("/requests/")
                    ? (
                        new URLSearchParams(location.search).get("from") ||
                        "/requests"
                      ).split("?")[0] === to
                    : isActive
                )
                  ? "active"
                  : ""
              }
              end={to === "/"}
              key={to}
              to={to}
              onClick={() => setOpen(false)}
            >
              <Icon size={19} />
              {title}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="secure-note">
            <ShieldCheck size={18} />
            <span>
              Información protegida
              <br />
              <small>Acceso según tus permisos</small>
            </span>
          </div>
          <div className="user-block">
            <div className="avatar">
              {user.name
                .split(" ")
                .slice(0, 2)
                .map((v) => v[0])
                .join("")}
            </div>
            <div>
              <b>{user.name}</b>
              <small>{labels[user.roles[0]]}</small>
            </div>
            <button
              onClick={logout}
              aria-label="Cerrar sesión"
              className="icon-btn"
            >
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <button
            className="mobile-menu icon-btn"
            onClick={() => setOpen(!open)}
            aria-label="Abrir menú"
          >
            <Menu />
          </button>
          <span>
            Gestión de ensayos <span className="top-divider">/</span>{" "}
            <b>Laboratorio</b>
          </span>
          <div>
            <span className="status-dot" /> Portal conectado
          </div>
        </header>
        <main>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/requests" element={<RequestList />} />
            <Route
              path="/requests/new"
              element={
                canRequest ? <RequestForm /> : <Navigate to="/requests" />
              }
            />
            <Route
              path="/requests/:id/edit"
              element={
                canRequest ? <RequestForm /> : <Navigate to="/requests" />
              }
            />
            <Route path="/requests/:id" element={<RequestDetail />} />
            <Route
              path="/reception"
              element={
                staff ? <RequestList mode="reception" /> : <Navigate to="/" />
              }
            />
            <Route
              path="/work"
              element={staff ? <WorkPage /> : <Navigate to="/" />}
            />
            <Route path="/reports" element={<ReportsPage />} />
            <Route
              path="/admin"
              element={
                user.roles.includes("ADMIN") ? <Admin /> : <Navigate to="/" />
              }
            />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
          <footer className="workspace-footer">
            Lara Consulting & Engineering{" "}
            <span>Laboratorio de suelos y relaves · Lurín</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
