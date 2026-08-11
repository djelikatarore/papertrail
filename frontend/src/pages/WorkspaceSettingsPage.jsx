import { Users } from "lucide-react";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import AppShell from "../components/AppShell";
import ConfirmDeleteModal from "../components/ConfirmDeleteModal";
import ErrorBanner from "../components/ErrorBanner";
import { useAuth } from "../context/AuthContext";
import { listMembers, listWorkspaces, removeMember } from "../services/workspaceService";

const TABS = [{ id: "members", label: "Members", icon: Users }];

function MembersTab({ workspaceId, isOwner }) {
  const { user } = useAuth();
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [removingMember, setRemovingMember] = useState(null);
  const [removing, setRemoving] = useState(false);
  const [removeError, setRemoveError] = useState(null);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceId]);

  function load() {
    setLoading(true);
    setError(null);
    listMembers(workspaceId)
      .then(setMembers)
      .catch(() => setError("Could not load workspace members. Please try again."))
      .finally(() => setLoading(false));
  }

  async function handleRemove() {
    if (removing || !removingMember) return;
    setRemoving(true);
    setRemoveError(null);
    try {
      await removeMember(workspaceId, removingMember.id);
      setMembers((prev) => prev.filter((m) => m.id !== removingMember.id));
      setRemovingMember(null);
    } catch (err) {
      setRemoveError(err.response?.data?.detail ?? "Could not remove this member. Please try again.");
    } finally {
      setRemoving(false);
    }
  }

  if (loading) return <p className="text-sm text-muted">Loading members...</p>;

  return (
    <div className="overflow-hidden rounded-[var(--radius-card-lg)] border border-border bg-card shadow-card">
      {error && (
        <div className="p-4">
          <ErrorBanner message={error} />
        </div>
      )}

      <div className="divide-y divide-border">
        {members.map((member) => {
          const isSelf = member.user_id === user?.id;
          return (
            <div key={member.id} className="flex items-center justify-between px-6 py-4">
              <div>
                <p className="text-sm font-semibold text-text">
                  {member.full_name} {isSelf && <span className="text-xs font-normal text-muted">(you)</span>}
                </p>
                <p className="text-xs text-muted">{member.email}</p>
                <p className="mt-0.5 text-xs text-muted">
                  {member.role} · Joined {member.joined_at ? new Date(member.joined_at).toLocaleDateString() : "—"}
                </p>
              </div>
              {isOwner && !isSelf && member.role !== "OWNER" && (
                <button
                  type="button"
                  onClick={() => {
                    setRemoveError(null);
                    setRemovingMember(member);
                  }}
                  className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold text-red transition-colors hover:bg-red-light"
                >
                  Remove
                </button>
              )}
            </div>
          );
        })}
      </div>

      {removingMember && (
        <ConfirmDeleteModal
          title={`Remove ${removingMember.full_name} from this workspace?`}
          description="They immediately lose access to this workspace and everything in it. Papers they've uploaded and comments they've written stay in place, still attributed to them — only their access is removed."
          confirmLabel="Remove member"
          deleting={removing}
          error={removeError}
          onConfirm={handleRemove}
          onClose={() => setRemovingMember(null)}
        />
      )}
    </div>
  );
}

export default function WorkspaceSettingsPage() {
  const { workspaceId } = useParams();
  const [tab, setTab] = useState("members");
  const [isOwner, setIsOwner] = useState(false);
  const [workspaceName, setWorkspaceName] = useState(null);

  useEffect(() => {
    listWorkspaces()
      .then((workspaces) => {
        const current = workspaces.find((w) => String(w.id) === String(workspaceId));
        setIsOwner(current?.role === "OWNER");
        setWorkspaceName(current?.name ?? null);
      })
      .catch(() => {});
  }, [workspaceId]);

  return (
    <AppShell workspaceId={workspaceId} title="Workspace Settings" subtitle={workspaceName}>
      <div className="max-w-2xl p-10">
        <div className="mb-7 flex w-fit gap-1 rounded-xl bg-app-bg p-1">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              aria-current={tab === t.id ? "page" : undefined}
              className={`flex items-center gap-2 rounded-lg px-4 py-1.5 text-sm transition-colors ${
                tab === t.id ? "bg-card font-semibold text-text shadow-card" : "text-muted"
              }`}
            >
              <t.icon size={14} /> {t.label}
            </button>
          ))}
        </div>

        {tab === "members" && <MembersTab workspaceId={workspaceId} isOwner={isOwner} />}
      </div>
    </AppShell>
  );
}
