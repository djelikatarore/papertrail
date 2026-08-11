import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import PasswordInput from "../components/PasswordInput";
import PasswordStrengthIndicator from "../components/PasswordStrengthIndicator";
import { useAuth } from "../context/AuthContext";
import useClearSensitiveFieldsOnRestore from "../hooks/useClearSensitiveFieldsOnRestore";
import { getCurrentUser, login, signup } from "../services/authService";
import { setToken } from "../services/tokenStore";
import { getInvitationPreview } from "../services/workspaceService";
import { isValidEmail } from "../utils/emailValidation";
import { getPasswordError, isAtMaxLength } from "../utils/passwordValidation";

export default function SignupPage() {
  const navigate = useNavigate();
  const { login: setAuth } = useAuth();
  const [searchParams] = useSearchParams();
  const redirect = searchParams.get("redirect");
  const inviteToken = searchParams.get("invite");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitError, setSubmitError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [invitation, setInvitation] = useState(null);
  const [invitationError, setInvitationError] = useState(null);

  useClearSensitiveFieldsOnRestore(() => {
    setEmail("");
    setPassword("");
    setConfirmPassword("");
  });

  // A valid invite link pre-fills and locks the email field — the backend
  // rejects signup if it doesn't match the invited address exactly, so
  // locking it here avoids a confusing rejection after filling the whole form.
  useEffect(() => {
    if (!inviteToken) return;
    getInvitationPreview(inviteToken)
      .then((preview) => {
        setInvitation(preview);
        setEmail(preview.email);
      })
      .catch(() => setInvitationError("This invitation link is invalid or has already been used."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inviteToken]);

  const emailError = email && !isValidEmail(email) ? "Please enter a valid email address." : null;
  const passwordError = password ? getPasswordError(password) : null;
  const confirmError =
    confirmPassword && confirmPassword !== password ? "Passwords do not match" : null;
  const passwordAtMax = isAtMaxLength(password);
  const confirmAtMax = isAtMaxLength(confirmPassword);

  const canSubmit =
    fullName.trim() &&
    email.trim() &&
    !emailError &&
    password &&
    confirmPassword &&
    !passwordError &&
    !confirmError &&
    !submitting;

  async function handleSubmit(event) {
    event.preventDefault();
    if (!canSubmit) return;

    setSubmitting(true);
    setSubmitError(null);
    try {
      await signup({ fullName, email, password, inviteToken });
    } catch (err) {
      setSubmitError(err.response?.data?.detail ?? "Signup failed. Please try again.");
      setSubmitting(false);
      return;
    }

    // The account now exists — from here on, any failure is a login/session
    // problem, never a "signup failed" one, so it must never be reported as
    // such (mirrors LoginPage's own credentials-vs-session distinction).
    try {
      const { access_token: token } = await login({ email, password });
      setToken(token);
      const user = await getCurrentUser();
      setAuth(token, user);
      navigate(redirect || "/dashboard");
    } catch {
      navigate(redirect ? `/login?redirect=${encodeURIComponent(redirect)}` : "/login");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-app-bg p-8">
      <div className="w-full max-w-sm rounded-[var(--radius-card-lg)] border border-border bg-card p-8 shadow-card">
        <h1 className="mb-6 text-2xl font-bold tracking-tight text-text">Sign up</h1>

        {invitation && (
          <div className="mb-5 rounded-lg bg-accent-light px-4 py-3 text-sm text-accent">
            You've been invited to join <strong>{invitation.workspace_name}</strong>.
          </div>
        )}
        {invitationError && (
          <div className="mb-5 rounded-lg bg-red-light px-4 py-3 text-sm text-red">{invitationError}</div>
        )}

        <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
          <div>
            <label className="mb-1 block text-sm font-semibold text-text">Full name</label>
            <input
              type="text"
              autoComplete="name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full rounded-xl border border-border px-3.5 py-2 text-sm outline-none transition-colors focus:border-accent"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-semibold text-text">Email</label>
            <input
              type="email"
              autoComplete="email"
              value={email}
              disabled={!!invitation}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-xl border border-border px-3.5 py-2 text-sm outline-none transition-colors focus:border-accent disabled:bg-app-bg disabled:text-muted"
            />
            {emailError && <p className="mt-1 text-xs text-red">{emailError}</p>}
          </div>

          <div>
            <label className="mb-1 block text-sm font-semibold text-text">Password</label>
            <PasswordInput
              value={password}
              autoComplete="new-password"
              onChange={(e) => setPassword(e.target.value)}
              className="rounded-xl border-border focus:border-accent"
            />
            {passwordError && <p className="mt-1 text-xs text-red">{passwordError}</p>}
            {!passwordError && passwordAtMax && (
              <p className="mt-1 text-xs text-muted">Maximum 12 characters reached</p>
            )}
            <PasswordStrengthIndicator password={password} />
          </div>

          <div>
            <label className="mb-1 block text-sm font-semibold text-text">
              Confirm password
            </label>
            <PasswordInput
              value={confirmPassword}
              autoComplete="new-password"
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="rounded-xl border-border focus:border-accent"
            />
            {confirmError && <p className="mt-1 text-xs text-red">{confirmError}</p>}
            {!confirmError && confirmAtMax && (
              <p className="mt-1 text-xs text-muted">Maximum 12 characters reached</p>
            )}
          </div>

          {submitError && <p className="text-sm text-red">{submitError}</p>}

          <button type="submit" disabled={!canSubmit} className="btn-primary mt-2 py-2.5">
            {submitting ? "Signing up..." : "Sign up"}
          </button>
        </form>

        <p className="mt-5 text-center text-sm text-muted">
          Already have an account?{" "}
          <Link
            to={redirect ? `/login?redirect=${encodeURIComponent(redirect)}` : "/login"}
            className="font-semibold text-accent"
          >
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}
