import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute() {
  const { token, checkingAuth, isLoggingOut } = useAuth();
  const location = useLocation();

  // A persisted token is still being verified against the backend — render
  // nothing rather than redirecting, or a refresh on an authenticated page
  // would flash to /login before we know the token is actually still valid.
  if (checkingAuth) {
    return null;
  }

  if (!token) {
    // An intentional logout must never preserve "return to this page" —
    // doing so can leak the page the previous account was on into the next
    // login (possibly a different account), landing them somewhere other
    // than /dashboard instead. Only a token that just expired/became
    // invalid while browsing should redirect back here after re-auth.
    if (isLoggingOut()) {
      return <Navigate to="/login" replace />;
    }
    const redirect = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?redirect=${redirect}`} replace />;
  }

  return <Outlet />;
}
