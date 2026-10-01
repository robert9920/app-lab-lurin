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
      <div className="workspace">
        <header className="portal-header">
          <NavLink to="/" className="brand">
            <img src="/logo.png" alt="Lara Consulting" />
            <span>LABORATORIO LURÍN</span>
          </NavLink>
          <button
            className="mobile-menu icon-btn"
            onClick={() => setOpen(!open)}
            aria-label="Abrir menú"
            aria-expanded={open}
          >
            <Menu />
          </button>
          <nav
            className={`workspace-nav ${open ? "open" : ""}`}
            aria-label="Espacio de trabajo"
          >
            {navigation.map(([to, title, Icon]) => (
              <NavLink
                end={to === "/"}
                key={to}
                to={to}
                onClick={() => setOpen(false)}
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
              >
                <Icon size={18} />
                {title}
              </NavLink>
            ))}
          </nav>
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
              title="Cerrar sesión"
              className="icon-btn"
            >
              <LogOut size={18} />
            </button>
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
