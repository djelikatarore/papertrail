import { FileText } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import ErrorBanner from "../components/ErrorBanner";
import PasswordInput from "../components/PasswordInput";
import { useAuth } from "../context/AuthContext";
import { getCurrentUser, login } from "../services/authService";
import { setToken } from "../services/tokenStore";

export default function LoginPage() {
  const navigate = useNavigate();
  const { login: setAuth } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!email.trim() || !password || submitting) return;

    setSubmitting(true);
    setError(null);
    try {
      const { access_token: token } = await login({ email, password });
      // getCurrentUser needs the token in place before its own request fires.
      setToken(token);
      const user = await getCurrentUser();
      setAuth(token, user);
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.detail ?? "Login failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0D0815]">
      <div className="w-full max-w-[400px] px-4">
        <div className="mb-8 text-center">
          <div className="mb-2 inline-flex items-center gap-2.5">
            <div className="flex h-[38px] w-[38px] items-center justify-center rounded-[11px] bg-accent">
              <FileText size={18} color="#fff" strokeWidth={1.5} />
            </div>
            <span className="text-2xl font-bold tracking-tight text-white">PaperTrail</span>
          </div>
          <p className="text-sm text-white/45">AI-powered academic research assistant</p>
        </div>

        <div className="rounded-[20px] border border-white/10 bg-white/[0.06] p-9 backdrop-blur-2xl">
          <h2 className="mb-1 text-xl font-bold text-white">Welcome back</h2>
          <p className="mb-7 text-sm text-white/45">Sign in to continue your research</p>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-white/55">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@university.edu"
                className="w-full rounded-lg border border-white/15 bg-white/[0.07] px-3.5 py-2.5 text-sm text-white outline-none"
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-white/55">Password</label>
              <PasswordInput
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="border-white/15 bg-white/[0.07] text-white"
              />
            </div>

            {error && <ErrorBanner message={error} />}

            <button
              type="submit"
              disabled={!email.trim() || !password || submitting}
              className="w-full rounded-lg bg-accent py-2.5 text-sm font-semibold text-white disabled:opacity-40"
            >
              {submitting ? "Signing in..." : "Sign in"}
            </button>
          </form>

          <p className="mt-5 text-center text-sm text-white/40">
            <Link to="/forgot-password" className="text-[#A78BFA]">
              Forgot password?
            </Link>
          </p>
          <p className="mt-2 text-center text-sm text-white/40">
            No account?{" "}
            <Link to="/signup" className="font-semibold text-[#A78BFA]">
              Sign up
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
