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
    <div className="flex min-h-screen items-center justify-center bg-app-bg">
      <div className="w-full max-w-sm rounded-card bg-white p-8 shadow-card">
        <h1 className="mb-6 text-xl font-semibold text-gray-900">Forgot password</h1>

        {message ? (
          <p className="text-sm text-gray-600">{message}</p>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>

            <button
              type="submit"
              disabled={!email.trim() || submitting}
              className="mt-2 rounded-card bg-accent px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
            >
              {submitting ? "Sending..." : "Send reset link"}
            </button>
          </form>
        )}

        <p className="mt-4 text-center text-sm text-gray-500">
          <Link to="/login" className="text-accent">
            Back to log in
          </Link>
        </p>
      </div>
    </div>
  );
}
