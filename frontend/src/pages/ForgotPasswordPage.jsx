import { useState } from "react";
import { Link } from "react-router-dom";
import { forgotPassword } from "../services/authService";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState(null);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!email.trim() || submitting) return;

    setSubmitting(true);
    try {
      const data = await forgotPassword(email);
      setMessage(data.message);
    } catch {
      setMessage("If an account with that email exists, a reset link has been sent.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-app-bg p-8">
      <div className="w-full max-w-sm rounded-[var(--radius-card-lg)] border border-border bg-card p-8 shadow-card">
        <h1 className="mb-6 text-2xl font-bold tracking-tight text-text">Forgot password</h1>

        {message ? (
          <p className="text-sm text-muted">{message}</p>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label className="mb-1 block text-sm font-semibold text-text">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-xl border border-border px-3.5 py-2 text-sm outline-none transition-colors focus:border-accent"
              />
            </div>

            <button type="submit" disabled={!email.trim() || submitting} className="btn-primary mt-2 py-2.5">
              {submitting ? "Sending..." : "Send reset link"}
            </button>
          </form>
        )}

        <p className="mt-5 text-center text-sm text-muted">
          <Link to="/login" className="font-semibold text-accent">
            Back to log in
          </Link>
        </p>
      </div>
    </div>
  );
}
