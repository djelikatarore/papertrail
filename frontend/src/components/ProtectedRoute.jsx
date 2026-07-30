import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute() {
  const { token, checkingAuth } = useAuth();

  // A persisted token is still being verified against the backend — render
  // nothing rather than redirecting, or a refresh on an authenticated page
  // would flash to /login before we know the token is actually still valid.
  if (checkingAuth) {
    return null;
  }

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
