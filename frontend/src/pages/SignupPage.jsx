import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import GoogleSignInButton from "../components/GoogleSignInButton";
import PasswordInput from "../components/PasswordInput";
import PasswordStrengthIndicator from "../components/PasswordStrengthIndicator";
import { useAuth } from "../context/AuthContext";
import useClearSensitiveFieldsOnRestore from "../hooks/useClearSensitiveFieldsOnRestore";
import { getCurrentUser, loginWithGoogle, signup } from "../services/authService";
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
  const [signupComplete, setSignupComplete] = useState(false);

  useClearSensitiveFieldsOnRestore(() => {
    setEmail("");
    setPassword("");
    setConfirmPassword("");
  });

  // Preserves both redirect and the invite token across a Signup <-> Login
  // hop — losing either would either strand the user post-login or turn
  // the unified invite link back into two disconnected flows.
  function loginUrlWithParams() {
    const params = new URLSearchParams();
    if (redirect) params.set("redirect", redirect);
    if (inviteToken) params.set("invite", inviteToken);
    const qs = params.toString();
    return qs ? `/login?${qs}` : "/login";
  }

  // A valid invite link pre-fills and locks the email field — the backend
  // rejects signup if it doesn't match the invited address exactly, so
  // locking it here avoids a confusing rejection after filling the whole form.
  // If the invited email already belongs to an account, Signup isn't the
  // right screen at all — redirect straight to Login (same token carried
  // over), where a confirmation step handles joining instead of an
  // automatic signup-time join.
  useEffect(() => {
    if (!inviteToken) return;
    getInvitationPreview(inviteToken)
      .then((preview) => {
        if (preview.account_exists) {
          navigate(loginUrlWithParams(), { replace: true });
          return;
        }
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

  async function handleGoogleToken(idToken) {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const { access_token: token } = await loginWithGoogle(idToken);
      setToken(token);
      const user = await getCurrentUser();
      setAuth(token, user);
      navigate(redirect || "/dashboard");
    } catch (err) {
      setSubmitError(err.response?.data?.detail ?? "Google sign-in failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (!canSubmit) return;

    setSubmitting(true);
    setSubmitError(null);
    try {
      await signup({ fullName, email, password, inviteToken });
      // Password-based accounts start unverified — the backend just sent a
      // confirmation email and login() would reject this account until the
      // link is clicked, so there's nothing to auto-login into yet (unlike
      // Google signup, which is verified immediately).
      setSignupComplete(true);
    } catch (err) {
      setSubmitError(err.response?.data?.detail ?? "Signup failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (signupComplete) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-app-bg p-8">
        <div className="w-full max-w-sm rounded-[var(--radius-card-lg)] border border-border bg-card p-8 text-center shadow-card">
          <h1 className="mb-3 text-2xl font-bold tracking-tight text-text">Check your email</h1>
          <p className="mb-6 text-sm text-muted">
            We sent a confirmation link to <strong className="text-text">{email}</strong>. Click it to activate
            your account, then log in.
          </p>
          <Link to="/login" className="btn-primary inline-flex px-4 py-2.5">
            Go to Log in
          </Link>
        </div>
      </div>
    );
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

        <div className="mb-5">
          <GoogleSignInButton onToken={handleGoogleToken} onError={setSubmitError} />
        </div>

        <div className="mb-5 flex items-center gap-3">
          <div className="h-px flex-1 bg-border" />
          <span className="text-xs text-muted">or</span>
          <div className="h-px flex-1 bg-border" />
        </div>

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
          <Link to={loginUrlWithParams()} className="font-semibold text-accent">
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}
