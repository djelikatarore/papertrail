import { FileText, GitBranch, MessageSquare, Sparkles } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import ErrorBanner from "../components/ErrorBanner";
import PasswordInput from "../components/PasswordInput";
import { useAuth } from "../context/AuthContext";
import useClearSensitiveFieldsOnRestore from "../hooks/useClearSensitiveFieldsOnRestore";
import { getCurrentUser, login } from "../services/authService";
import { setToken } from "../services/tokenStore";
import { isValidEmail } from "../utils/emailValidation";

export default function LoginPage() {
  const navigate = useNavigate();
  const { login: setAuth } = useAuth();
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useClearSensitiveFieldsOnRestore(() => {
    setEmail("");
    setPassword("");
  });
  // Set once from the URL on first render (the interceptor redirects here
  // with ?sessionExpired=1) — distinct from `error`, which only ever reflects
  // the outcome of an actual submit below. Cleared as soon as the user starts
  // typing, so it can't linger and be confused with a fresh submit's result.
  const [sessionExpired, setSessionExpired] = useState(searchParams.get("sessionExpired") === "1");
  const redirect = searchParams.get("redirect");

  async function handleSubmit(event) {
    event.preventDefault();
    if (!email.trim() || !password || submitting) return;

    if (!isValidEmail(email)) {
      setError("Please enter a valid email address.");
      return;
    }

    setSubmitting(true);
    setError(null);
    let token;
    try {
      ({ access_token: token } = await login({ email, password }));
    } catch (err) {
      // Only the login call itself can produce "Incorrect email or password" —
      // this is always the backend's real credential check, never a stale or
      // expired token from a previous session (login doesn't look at any
      // existing token at all).
      setError(err.response?.data?.detail ?? "Login failed. Please try again.");
      setSubmitting(false);
      return;
    }

    try {
      // getCurrentUser needs the token in place before its own request fires.
      setToken(token);
      const user = await getCurrentUser();
      setAuth(token, user);
      navigate(redirect || "/dashboard");
    } catch {
      // Credentials were genuinely correct (login succeeded) — a failure here
      // is a different, real problem (e.g. the API being unreachable), so it
      // must never be reported as a credentials error.
      setError("Logged in, but could not load your account. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  const features = [
    { icon: Sparkles, label: "Instant AI Summaries", desc: "Key contributions extracted automatically" },
    { icon: GitBranch, label: "Semantic Discovery", desc: "Find related papers across your workspace" },
    { icon: MessageSquare, label: "Grounded Conversations", desc: "Ask questions, get answers cited to source" },
  ];

  return (
    <div className="flex min-h-screen bg-app-bg">
      <div className="hidden w-[420px] shrink-0 flex-col justify-center bg-sidebar p-12 lg:flex">
        <div className="mb-10 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent shadow-[0_8px_24px_-4px_rgba(124,58,237,0.35)]">
            <FileText size={18} color="#fff" strokeWidth={1.5} />
          </div>
          <span className="text-xl font-bold tracking-tight text-white">PaperTrail</span>
        </div>
        <h1 className="mb-3 text-3xl font-bold leading-tight tracking-tight text-white">
          Your AI-powered
          <br />
          research companion
        </h1>
        <p className="mb-10 text-sm leading-relaxed text-white/40">
          Upload papers, generate summaries, discover connections, and ask grounded questions across
          your research library.
        </p>
        <div className="flex flex-col gap-5">
          {features.map(({ icon: Icon, label, desc }) => (
            <div key={label} className="flex items-start gap-3.5">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-accent/25 bg-accent/20">
                <Icon size={15} className="text-accent" strokeWidth={1.5} />
              </div>
              <div>
                <p className="text-sm font-semibold text-white">{label}</p>
                <p className="mt-0.5 text-xs text-white/40">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex flex-1 items-center justify-center p-8">
        <div className="w-full max-w-sm">
          <div className="mb-8 text-center lg:hidden">
            <div className="mb-2 inline-flex items-center gap-2.5">
              <div className="flex h-[38px] w-[38px] items-center justify-center rounded-xl bg-accent">
                <FileText size={18} color="#fff" strokeWidth={1.5} />
              </div>
              <span className="text-2xl font-bold tracking-tight text-text">PaperTrail</span>
            </div>
          </div>

          <h2 className="mb-1 text-2xl font-bold tracking-tight text-text">Welcome back</h2>
          <p className="mb-7 text-sm text-muted">Log in to continue your research</p>

          {sessionExpired && (
            <div className="mb-4">
              <ErrorBanner message="Your session has expired. Please log in again." />
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
            <div>
              <label className="mb-1.5 block text-sm font-semibold text-text">Email</label>
              <input
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  setSessionExpired(false);
                  setError(null);
                }}
                placeholder="you@example.com"
                className="w-full rounded-xl border border-border bg-card px-3.5 py-2.5 text-sm text-text shadow-card outline-none transition-colors focus:border-accent"
              />
            </div>

            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <label className="block text-sm font-semibold text-text">Password</label>
                <Link to="/forgot-password" className="text-xs font-semibold text-accent">
                  Forgot password?
                </Link>
              </div>
              <PasswordInput
                value={password}
                autoComplete="current-password"
                onChange={(e) => {
                  setPassword(e.target.value);
                  setSessionExpired(false);
                  setError(null);
                }}
                className="rounded-xl border-border py-2.5 shadow-card focus:border-accent"
              />
            </div>

            {error && <ErrorBanner message={error} />}

            <button
              type="submit"
              disabled={!email.trim() || !password || submitting}
              className="btn-primary mt-1 w-full py-2.5"
            >
              {submitting ? "Logging in..." : "Log in"}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-muted">
            No account?{" "}
            <Link
              to={redirect ? `/signup?redirect=${encodeURIComponent(redirect)}` : "/signup"}
              className="font-semibold text-accent"
            >
              Sign up
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
