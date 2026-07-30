import { X } from "lucide-react";
import { useEffect, useState } from "react";
import { getProjectAccess, updateProjectAccess } from "../services/projectService";
import { listMembers } from "../services/workspaceService";
import ErrorBanner from "./ErrorBanner";

export default function ManageAccessPanel({ workspaceId, projectId, onClose }) {
  const [members, setMembers] = useState([]);
  const [restrictedIds, setRestrictedIds] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [togglingId, setTogglingId] = useState(null);

  useEffect(() => {
    loadState();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function loadState() {
    setLoading(true);
    setError(null);
    Promise.all([listMembers(workspaceId), getProjectAccess(workspaceId, projectId)])
      .then(([memberList, access]) => {
        setMembers(memberList);
        setRestrictedIds(new Set(access.restricted_member_ids));
      })
      .catch(() => setError("Could not load workspace members. Please try again."))
      .finally(() => setLoading(false));
  }

  function toggleMember(member) {
    const isRestricted = restrictedIds.has(member.id);
    setTogglingId(member.id);
    setError(null);

    const request = isRestricted
      ? // Re-granting access: revoke_member_id only ever adds a restriction, so
        // regaining access means resending the full allow-list of everyone who
        // should have access (every non-owner member not otherwise restricted).
        updateProjectAccess(workspaceId, projectId, {
          allowed_member_ids: members
            .filter((m) => m.role !== "OWNER")
            .filter((m) => !restrictedIds.has(m.id) || m.id === member.id)
            .map((m) => m.id),
        })
      : updateProjectAccess(workspaceId, projectId, { revoke_member_id: member.id });

    request
      .then((access) => setRestrictedIds(new Set(access.restricted_member_ids)))
      .catch(() => setError("Could not update access. Please try again."))
      .finally(() => setTogglingId(null));
  }

  return (
    <div className="fixed inset-0 z-[300] flex items-center justify-center bg-text/40">
      <div className="w-full max-w-md rounded-card bg-card p-8 shadow-card-hover">
        <div className="mb-5 flex items-center justify-between">
          <h3 className="text-lg font-bold text-text">Manage access</h3>
          <button type="button" onClick={onClose} className="text-muted">
            <X size={18} />
          </button>
        </div>

        {error && (
          <div className="mb-4">
            <ErrorBanner message={error} />
          </div>
        )}

        {loading ? (
          <p className="text-sm text-muted">Loading members...</p>
        ) : (
          <div className="flex flex-col gap-2">
            {members.map((member) => {
              const isOwner = member.role === "OWNER";
              const hasAccess = isOwner || !restrictedIds.has(member.id);
              return (
                <div
                  key={member.id}
                  className="flex items-center justify-between rounded-lg border border-border px-4 py-2.5"
                >
                  <div>
                    <p className="text-sm font-medium text-text">{member.full_name}</p>
                    <p className="text-xs text-muted">{member.email}</p>
                  </div>
                  <button
                    type="button"
                    disabled={isOwner || togglingId === member.id}
                    onClick={() => toggleMember(member)}
                    className={`h-6 w-11 shrink-0 rounded-full transition-colors disabled:opacity-40 ${
                      hasAccess ? "bg-accent" : "bg-border"
                    }`}
                    aria-label={hasAccess ? "Revoke access" : "Grant access"}
                  >
                    <span
                      className={`block h-5 w-5 translate-y-0.5 rounded-full bg-white transition-transform ${
                        hasAccess ? "translate-x-[22px]" : "translate-x-0.5"
                      }`}
                    />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
