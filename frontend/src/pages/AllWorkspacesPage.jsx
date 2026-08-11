import { Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import ConfirmDeleteModal from "../components/ConfirmDeleteModal";
import ErrorBanner from "../components/ErrorBanner";
import Modal from "../components/Modal";
import WorkspaceCard from "../components/WorkspaceCard";
import { deleteWorkspace, listWorkspaces, updateWorkspace } from "../services/workspaceService";

const SORT_OPTIONS = [
  { value: "recent", label: "Most recent" },
  { value: "name", label: "Name" },
];

export default function AllWorkspacesPage() {
  const navigate = useNavigate();

  const [workspaces, setWorkspaces] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("recent");

  const [renamingWorkspace, setRenamingWorkspace] = useState(null);
  const [renameValue, setRenameValue] = useState("");
  const [renaming, setRenaming] = useState(false);
  const [renameError, setRenameError] = useState(null);

  const [deletingWorkspace, setDeletingWorkspace] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState(null);

  useEffect(() => {
    load();
  }, []);

  function load() {
    setLoading(true);
    listWorkspaces()
      .then(setWorkspaces)
      .catch(() => setError("Could not load your workspaces. Please try again."))
      .finally(() => setLoading(false));
  }

  function openRename(workspace) {
    setRenamingWorkspace(workspace);
    setRenameValue(workspace.name);
    setRenameError(null);
  }

  async function handleRename(event) {
    event.preventDefault();
    if (!renameValue.trim() || renaming) return;
    setRenaming(true);
    setRenameError(null);
    try {
      const updated = await updateWorkspace(renamingWorkspace.id, { name: renameValue.trim() });
      setWorkspaces((prev) => prev.map((w) => (w.id === updated.id ? { ...w, name: updated.name } : w)));
      setRenamingWorkspace(null);
    } catch {
      setRenameError("Could not rename this workspace. Please try again.");
    } finally {
      setRenaming(false);
    }
  }

  async function handleDelete() {
    if (deleting || !deletingWorkspace) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteWorkspace(deletingWorkspace.id);
      setWorkspaces((prev) => prev.filter((w) => w.id !== deletingWorkspace.id));
      setDeletingWorkspace(null);
    } catch {
      setDeleteError("Could not delete this workspace. Please try again.");
    } finally {
      setDeleting(false);
    }
  }

  const visibleWorkspaces = useMemo(() => {
    const query = search.trim().toLowerCase();
    const filtered = query ? workspaces.filter((w) => w.name.toLowerCase().includes(query)) : workspaces;
    const sorted = [...filtered];
    if (sortBy === "name") {
      sorted.sort((a, b) => a.name.localeCompare(b.name));
    } else {
      sorted.sort((a, b) => new Date(b.created_at ?? 0) - new Date(a.created_at ?? 0));
    }
    return sorted;
  }, [workspaces, search, sortBy]);

  return (
    <AppShell title="All Workspaces" subtitle={`${workspaces.length} workspaces`}>
      <div className="p-10">
        <div className="mb-6 flex gap-2.5">
          <div className="relative flex-1">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search workspaces by name…"
              className="w-full rounded-xl border border-border py-2 pl-9 pr-3.5 text-sm text-text outline-none transition-colors focus:border-accent"
            />
          </div>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="rounded-xl border border-border px-3.5 py-2 text-sm text-text outline-none transition-colors focus:border-accent"
          >
            {SORT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                Sort: {opt.label}
              </option>
            ))}
          </select>
        </div>

        {error && (
          <div className="mb-6">
            <ErrorBanner message={error} />
          </div>
        )}

        {!loading && visibleWorkspaces.length === 0 && (
          <p className="py-10 text-center text-sm text-muted">
            {search ? "No workspaces match your search." : "You don't belong to any workspace yet."}
          </p>
        )}

        <div className="grid grid-cols-3 gap-4">
          {visibleWorkspaces.map((w) => (
            <WorkspaceCard
              key={w.id}
              workspace={w}
              onClick={() => navigate(`/workspaces/${w.id}`)}
              onRename={openRename}
              onDelete={setDeletingWorkspace}
            />
          ))}
        </div>
      </div>

      {renamingWorkspace && (
        <Modal onClose={() => (renaming ? null : setRenamingWorkspace(null))} maxWidth="max-w-sm">
          <h3 className="mb-6 pr-6 text-lg font-bold text-text">Rename Workspace</h3>
          <form onSubmit={handleRename} className="flex flex-col gap-4">
            <div>
              <label className="mb-1 block text-sm font-semibold text-text">Workspace name</label>
              <input
                type="text"
                value={renameValue}
                onChange={(e) => setRenameValue(e.target.value)}
                className="w-full rounded-lg border border-border px-3.5 py-2 text-sm"
              />
            </div>
            {renameError && <ErrorBanner message={renameError} />}
            <div className="mt-2 flex gap-2.5">
              <button
                type="button"
                onClick={() => setRenamingWorkspace(null)}
                disabled={renaming}
                className="btn-secondary flex-1 py-2.5"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!renameValue.trim() || renaming}
                className="btn-primary flex-1 py-2.5"
              >
                {renaming ? "Saving..." : "Save"}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {deletingWorkspace && (
        <ConfirmDeleteModal
          title={`Delete "${deletingWorkspace.name}"?`}
          description="This permanently deletes this workspace and everything in it — every project, paper, draft, review comment, chat history, and member. This cannot be undone."
          confirmLabel="Delete workspace"
          deleting={deleting}
          error={deleteError}
          onConfirm={handleDelete}
          onClose={() => setDeletingWorkspace(null)}
        />
      )}
    </AppShell>
  );
}
