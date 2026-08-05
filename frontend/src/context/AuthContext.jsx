import { createContext, useContext, useEffect, useRef, useState } from "react";
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
  // A ref (not state) so it's readable synchronously the instant logout() is
  // called, before any re-render — ProtectedRoute reads this to tell an
  // intentional logout apart from a token just expiring/becoming invalid
  // while the user is browsing. Without this distinction, ProtectedRoute's
  // own token-loss redirect can fire while the page being logged out from is
  // still mounted and append `?redirect=<that page>`, so the *next* login
  // (possibly as a different account) lands back there instead of
  // /dashboard — a stale-destination bug, not just a cosmetic one.
  const loggingOutRef = useRef(false);

  useEffect(() => {
    if (!token) {
      setCheckingAuth(false);
      return;
    }
    // Only runs once, to re-verify a token already persisted from a previous
    // session (see the eslint-disable below). If the user logs out and back
    // in as someone else before this in-flight request resolves, its result
    // is for a token that's no longer current — applying it would silently
    // overwrite the new account's data with the old one's. Every callback
    // below re-checks against the live token before touching state.
    const tokenAtRequestTime = token;
    getCurrentUser()
      .then((fetchedUser) => {
        if (getToken() === tokenAtRequestTime) {
          setUser(fetchedUser);
        }
      })
      .catch(() => {
        if (getToken() === tokenAtRequestTime) {
          clearToken();
          setToken(null);
          setUser(null);
        }
      })
      .finally(() => setCheckingAuth(false));
    // Only re-run on a real token change (e.g. login()/logout()), not on
    // every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function login(newToken, newUser) {
    loggingOutRef.current = false;
    setStoredToken(newToken);
    setToken(newToken);
    setUser(newUser);
  }

  function logout() {
    loggingOutRef.current = true;
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
    <AuthContext.Provider
      value={{ token, user, login, logout, updateUser, checkingAuth, isLoggingOut: () => loggingOutRef.current }}
    >
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
