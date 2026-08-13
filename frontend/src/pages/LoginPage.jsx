import { FileText, GitBranch, MessageSquare, Sparkles } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import ErrorBanner from "../components/ErrorBanner";
import GoogleSignInButton from "../components/GoogleSignInButton";
import PasswordInput from "../components/PasswordInput";
import { useAuth } from "../context/AuthContext";
import useClearSensitiveFieldsOnRestore from "../hooks/useClearSensitiveFieldsOnRestore";
import { getCurrentUser, login, loginWithGoogle } from "../services/authService";
import { clearRememberedEmail, getRememberedEmail, setRememberedEmail, setToken } from "../services/tokenStore";
import { isValidEmail } from "../utils/emailValidation";
import { acceptInvitation, getInvitationPreview } from "../services/workspaceService";

export default function LoginPage() {
  const navigate = useNavigate();
  const { login: setAuth } = useAuth();
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState(getRememberedEmail);
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(true);
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
  const inviteToken = searchParams.get("invite");

  const [pendingInvitation, setPendingInvitation] = useState(null);
  const [showInviteConfirm, setShowInviteConfirm] = useState(false);
  const [inviteActing, setInviteActing] = useState(false);
  const [inviteActionError, setInviteActionError] = useState(null);

  // Only reached when ?invite= is present — normal login (no invite param)
  // always takes the plain navigate(redirect || "/dashboard") branch below,
  // completely unchanged. An invalid/already-used invitation on this URL
  // doesn't block login — it just falls through to the normal destination
  // instead of showing a confirmation for an invitation that no longer exists.
  async function afterLoginSuccess() {
    if (inviteToken) {
      try {
        const preview = await getInvitationPreview(inviteToken);
        setPendingInvitation(preview);
        setShowInviteConfirm(true);
        return;
      } catch {
        // fall through to normal navigation below
      }
    }
    navigate(redirect || "/dashboard");
  }

  async function handleAcceptInvitation() {
    setInviteActing(true);
    setInviteActionError(null);
    try {
      const res = await acceptInvitation(inviteToken);
      navigate(`/workspaces/${res.workspace_id}`);
    } catch (err) {
      setInviteActionError(err.response?.data?.detail ?? "Could not accept this invitation. Please try again.");
    } finally {
      setInviteActing(false);
    }
  }

  function handleSkipInvitation() {
    navigate(redirect || "/dashboard");
  }

  function signupUrlWithParams() {
    const params = new URLSearchParams();
    if (redirect) params.set("redirect", redirect);
    if (inviteToken) params.set("invite", inviteToken);
    const qs = params.toString();
    return qs ? `/signup?${qs}` : "/signup";
  }

  async function handleGoogleToken(idToken) {
    setSubmitting(true);
    setError(null);
    try {
      const { access_token: token } = await loginWithGoogle(idToken);
      setToken(token, true);
      const user = await getCurrentUser();
      setAuth(token, user, true);
      await afterLoginSuccess();
    } catch (err) {
      setError(err.response?.data?.detail ?? "Google sign-in failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

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
      setToken(token, rememberMe);
      if (rememberMe) {
        setRememberedEmail(email);
      } else {
        clearRememberedEmail();
      }
      const user = await getCurrentUser();
      setAuth(token, user, rememberMe);
      await afterLoginSuccess();
    } catch {
      // Credentials were genuinely correct (login succeeded) — a failure here
      // is a different, real problem (e.g. the API being unreachable), so it
      // must never be reported as a credentials error.
      setError("Logged in, but could not load your account. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (showInviteConfirm && pendingInvitation) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-app-bg p-8">
        <div className="w-full max-w-sm rounded-[var(--radius-card-lg)] border border-border bg-card p-8 text-center shadow-card">
          <h1 className="mb-3 text-2xl font-bold tracking-tight text-text">You've been invited</h1>
          <p className="mb-6 text-sm text-muted">
            You've been invited to join{" "}
            <strong className="text-text">{pendingInvitation.workspace_name}</strong>.
          </p>
          {inviteActionError && (
            <div className="mb-4 text-left">
              <ErrorBanner message={inviteActionError} />
            </div>
          )}
          <div className="flex gap-2.5">
            <button
              type="button"
              onClick={handleSkipInvitation}
              disabled={inviteActing}
              className="btn-secondary flex-1 py-2.5"
            >
              Skip
            </button>
            <button
              type="button"
              onClick={handleAcceptInvitation}
              disabled={inviteActing}
              className="btn-primary flex-1 py-2.5"
            >
              {inviteActing ? "Joining..." : "Accept"}
            </button>
          </div>
        </div>
      </div>
    );
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

          <div className="mb-5">
            <GoogleSignInButton onToken={handleGoogleToken} onError={setError} />
          </div>

          <div className="mb-5 flex items-center gap-3">
            <div className="h-px flex-1 bg-border" />
            <span className="text-xs text-muted">or</span>
            <div className="h-px flex-1 bg-border" />
          </div>

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

            <label className="flex items-center gap-2 text-sm text-muted">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="h-4 w-4 rounded border-border text-accent focus:ring-accent"
              />
              Remember me
            </label>

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
            <Link to={signupUrlWithParams()} className="font-semibold text-accent">
              Sign up
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
