import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import PasswordInput from "../components/PasswordInput";
import PasswordStrengthIndicator from "../components/PasswordStrengthIndicator";
import { resetPassword } from "../services/authService";
import { getPasswordError, isAtMaxLength } from "../utils/passwordValidation";

export default function ResetPasswordPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitError, setSubmitError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const passwordError = password ? getPasswordError(password) : null;
  const confirmError =
    confirmPassword && confirmPassword !== password ? "Passwords do not match" : null;
  const passwordAtMax = isAtMaxLength(password);
  const confirmAtMax = isAtMaxLength(confirmPassword);

  const canSubmit = token && password && confirmPassword && !passwordError && !confirmError && !submitting;

  async function handleSubmit(event) {
    event.preventDefault();
    if (!canSubmit) return;

    setSubmitting(true);
    setSubmitError(null);
    try {
      await resetPassword({ token, newPassword: password });
      setDone(true);
      setTimeout(() => navigate("/login"), 2000);
    } catch (err) {
      setSubmitError(err.response?.data?.detail ?? "Could not reset password. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-app-bg">
      <div className="w-full max-w-sm rounded-card bg-white p-8 shadow-card">
        <h1 className="mb-6 text-xl font-semibold text-gray-900">Reset password</h1>

        {done ? (
          <p className="text-sm text-gray-600">
            Password updated. Redirecting to login...
          </p>
        ) : !token ? (
          <p className="text-sm text-red-600">
            No reset token found in the link. Please use the link from your email.
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                New password
              </label>
              <PasswordInput value={password} onChange={(e) => setPassword(e.target.value)} />
              {passwordError && <p className="mt-1 text-xs text-red-600">{passwordError}</p>}
              {!passwordError && passwordAtMax && (
                <p className="mt-1 text-xs text-gray-500">Maximum 12 characters reached</p>
              )}
              <PasswordStrengthIndicator password={password} />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Confirm new password
              </label>
              <PasswordInput
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
              />
              {confirmError && <p className="mt-1 text-xs text-red-600">{confirmError}</p>}
              {!confirmError && confirmAtMax && (
                <p className="mt-1 text-xs text-gray-500">Maximum 12 characters reached</p>
              )}
            </div>

            {submitError && <p className="text-sm text-red-600">{submitError}</p>}

            <button
              type="submit"
              disabled={!canSubmit}
              className="mt-2 rounded-card bg-accent px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
            >
              {submitting ? "Resetting..." : "Reset password"}
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
