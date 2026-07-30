import { createContext, useContext, useEffect, useState } from "react";
import { getCurrentUser } from "../services/authService";
import { getToken, setToken as setStoredToken, clearToken } from "../services/tokenStore";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(getToken());
  const [user, setUser] = useState(null);
  // True only while a persisted token is being re-verified against the
  // backend on first load — ProtectedRoute must not redirect to /login
  // during this window, or a refresh on an authenticated page would flash
  // to the login screen before we know the token is actually still valid.
  const [checkingAuth, setCheckingAuth] = useState(!!getToken());

  useEffect(() => {
    if (!token) {
      setCheckingAuth(false);
      return;
    }
    getCurrentUser()
      .then(setUser)
      .catch(() => {
        clearToken();
        setToken(null);
        setUser(null);
      })
      .finally(() => setCheckingAuth(false));
    // Only re-run on a real token change (e.g. login()/logout()), not on
    // every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  // Merges fresh fields (e.g. after a profile edit) into the current user so
  // every consumer of useAuth() (AvatarMenu, Settings) re-renders with the
  // new value immediately, without needing a fresh /auth/me round trip.
  function updateUser(partialUser) {
    setUser((prev) => (prev ? { ...prev, ...partialUser } : prev));
  }

  return (
    <AuthContext.Provider value={{ token, user, login, logout, updateUser, checkingAuth }}>
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
