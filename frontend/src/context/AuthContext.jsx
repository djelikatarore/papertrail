import { createContext, useContext, useState } from "react";
import { setToken as setStoredToken, clearToken } from "../services/tokenStore";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);

  // Kept in memory only (no localStorage) — a page refresh logs the user
  // out for now. Revisit with persistence once the auth flow is settled.
  function login(newToken, newUser) {
    setStoredToken(newToken);
    setToken(newToken);
    setUser(newUser);
  }

  function logout() {
    clearToken();
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ token, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
