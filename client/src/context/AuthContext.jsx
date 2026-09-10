import { createContext, useContext, useEffect, useState } from "react";
import { api, setCsrf } from "../services/api";
const AuthContext = createContext(null);
export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(null),
    [loading, setLoading] = useState(true);
  function accept(data) {
    setCsrf(data?.csrf);
    setAuth(data);
  }
  useEffect(() => {
    api
      .get("/session")
      .then((r) => accept(r.data))
      .catch(() => accept(null))
      .finally(() => setLoading(false));
    const expire = () => accept(null);
    window.addEventListener("session-expired", expire);
    return () => window.removeEventListener("session-expired", expire);
  }, []);
  async function logout() {
    try {
      await api.post("/auth/logout", {});
    } finally {
      accept(null);
    }
  }
  return (
    <AuthContext.Provider
      value={{ auth, user: auth?.user, loading, accept, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}
export const useAuth = () => useContext(AuthContext);
