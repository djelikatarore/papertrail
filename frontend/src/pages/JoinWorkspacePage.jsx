import { FileText } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { joinWorkspace } from "../services/workspaceService";

export default function JoinWorkspacePage() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [error, setError] = useState(null);
  // React 18 StrictMode (dev only) double-invokes effects, which would fire
  // this join request twice concurrently — the backend's membership check
  // isn't atomic, so two concurrent requests can both pass the "not already
  // a member" check before either commits. Guard here so only one request is
  // ever actually sent per token, regardless of how many times the effect runs.
  const attempted = useRef(false);

  useEffect(() => {
    if (attempted.current) return;
    attempted.current = true;

    joinWorkspace(token)
      .then((workspace) => navigate(`/workspaces/${workspace.id}`, { replace: true }))
      .catch((err) => {
        const status = err.response?.status;
        if (status === 409) {
          setError("You're already a member of this workspace.");
        } else if (status === 404) {
          setError("This invite link is invalid or has expired.");
        } else {
          setError("Could not join this workspace. Please try again.");
        }
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-app-bg">
      <div className="w-full max-w-sm rounded-[var(--radius-card-lg)] border border-border bg-card p-8 text-center shadow-card">
        <div className="mb-4 inline-flex h-[38px] w-[38px] items-center justify-center rounded-xl bg-accent">
          <FileText size={18} color="#fff" strokeWidth={1.5} />
        </div>
        {error ? (
          <>
            <p className="mb-4 text-sm text-text">{error}</p>
            <Link to="/dashboard" className="text-sm font-semibold text-accent">
              Go to Dashboard
            </Link>
          </>
        ) : (
          <p className="text-sm text-muted">Joining workspace...</p>
        )}
      </div>
    </div>
  );
}
