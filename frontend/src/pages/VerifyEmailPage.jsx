import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { verifyEmail } from "../services/authService";

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [status, setStatus] = useState(token ? "verifying" : "missing"); // "verifying" | "success" | "error" | "missing"
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!token) return;
    verifyEmail(token)
      .then(() => setStatus("success"))
      .catch((err) => {
        setError(err.response?.data?.detail ?? "Could not verify this email.");
        setStatus("error");
      });
  }, [token]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-app-bg p-8">
      <div className="w-full max-w-sm rounded-[var(--radius-card-lg)] border border-border bg-card p-8 text-center shadow-card">
        <h1 className="mb-3 text-2xl font-bold tracking-tight text-text">Email verification</h1>

        {status === "verifying" && <p className="text-sm text-muted">Verifying your email…</p>}

        {status === "missing" && (
          <p className="text-sm text-red">No verification token found in the link. Please use the link from your email.</p>
        )}

        {status === "success" && (
          <>
            <p className="mb-6 text-sm text-muted">Your email has been verified. You can now log in.</p>
            <Link to="/login" className="btn-primary inline-flex px-4 py-2.5">
              Go to Log in
            </Link>
          </>
        )}

        {status === "error" && (
          <>
            <p className="mb-6 text-sm text-red">{error}</p>
            <Link to="/signup" className="font-semibold text-accent">
              Back to sign up
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
