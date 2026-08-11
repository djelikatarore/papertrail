import { FolderOpen, Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import ErrorBanner from "../components/ErrorBanner";
import Modal from "../components/Modal";
import ProjectCard from "../components/ProjectCard";
import { useAuth } from "../context/AuthContext";
import { createWorkspace, listProjects, listWorkspaces } from "../services/workspaceService";

export default function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [workspace, setWorkspace] = useState(null);
  const [recentProjects, setRecentProjects] = useState([]);
  const [projectsTotal, setProjectsTotal] = useState(0);
  const [newWorkspaceName, setNewWorkspaceName] = useState("");
  const [creatingWorkspace, setCreatingWorkspace] = useState(false);
  const [showCreateWorkspace, setShowCreateWorkspace] = useState(false);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function load() {
    setLoading(true);
    setError(null);
    listWorkspaces()
      .then((workspaces) => {
        if (workspaces.length === 0) {
          setWorkspace(null);
          return;
        }
        const first = workspaces[0];
        setWorkspace(first);
        return listProjects(first.id, { page: 1, limit: 4 }).then((res) => {
          setRecentProjects(res.items);
          setProjectsTotal(res.total);
        });
      })
      .catch(() => setError("Could not load your workspace. Please try again."))
      .finally(() => setLoading(false));
  }

  async function handleCreateWorkspace(event) {
    event.preventDefault();
    if (!newWorkspaceName.trim() || creatingWorkspace) return;
    setCreatingWorkspace(true);
    try {
      await createWorkspace({ name: newWorkspaceName.trim() });
      setNewWorkspaceName("");
      setShowCreateWorkspace(false);
      load();
    } catch {
      setError("Could not create workspace. Please try again.");
    } finally {
      setCreatingWorkspace(false);
    }
  }

  if (loading) {
    return (
      <AppShell title="Dashboard" showBack={false}>
        <div className="p-10 text-sm text-muted">Loading...</div>
      </AppShell>
    );
  }

  if (!workspace) {
    return (
      <AppShell title="Dashboard" showBack={false}>
        <div className="mx-auto max-w-md p-10">
          <div className="rounded-[var(--radius-card-lg)] border border-border bg-card p-8 shadow-card">
            <h2 className="mb-2 text-lg font-bold text-text">Create your first workspace</h2>
            <p className="mb-5 text-sm text-muted">
              A workspace holds your projects and papers. You don't have one yet.
            </p>
            {error && (
              <div className="mb-4">
                <ErrorBanner message={error} />
              </div>
            )}
            <form onSubmit={handleCreateWorkspace} className="flex gap-2">
              <input
                type="text"
                value={newWorkspaceName}
                onChange={(e) => setNewWorkspaceName(e.target.value)}
                placeholder="e.g. MIT Research Lab"
                className="flex-1 rounded-xl border border-border px-3.5 py-2 text-sm outline-none transition-colors focus:border-accent"
              />
              <button
                type="submit"
                disabled={!newWorkspaceName.trim() || creatingWorkspace}
                className="btn-primary px-4 py-2"
              >
                Create
              </button>
            </form>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell workspaceId={workspace.id} title="Dashboard" subtitle={workspace.name} showBack={false}>
      <div className="p-10">
        <div className="mb-7 flex items-center justify-between">
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-accent">Overview</p>
            <p className="text-sm text-muted">
              {user ? `Welcome back, ${user.full_name}` : ""}
            </p>
          </div>
          <button type="button" onClick={() => setShowCreateWorkspace(true)} className="btn-primary px-4 py-2">
            <Plus size={15} /> Create Workspace
          </button>
        </div>

        {error && (
          <div className="mb-6">
            <ErrorBanner message={error} />
          </div>
        )}

        <div className="mb-8 grid grid-cols-4 gap-4">
          <div className="rounded-[var(--radius-card-lg)] border border-border bg-card p-5 shadow-card transition-shadow hover:shadow-card-hover">
            <div className="mb-3.5 flex h-10 w-10 items-center justify-center rounded-xl bg-accent-light">
              <FolderOpen size={18} className="text-accent" strokeWidth={1.5} />
            </div>
            <p className="mb-0.5 text-[26px] font-bold tracking-tight text-text">{projectsTotal}</p>
            <p className="text-xs text-muted">Projects</p>
          </div>
        </div>

        <div className="mb-3.5 flex items-center justify-between">
          <h3 className="text-[15px] font-bold text-text">Recent Projects</h3>
          <button
            type="button"
            onClick={() => navigate(`/workspaces/${workspace.id}`)}
            className="text-sm font-semibold text-accent"
          >
            View all
          </button>
        </div>

        {recentProjects.length === 0 ? (
          <button
            type="button"
            onClick={() => navigate(`/workspaces/${workspace.id}`)}
            className="flex w-full flex-col items-center gap-2.5 rounded-[var(--radius-card-lg)] border-2 border-dashed border-border py-10 text-muted transition-colors hover:border-accent/40 hover:text-accent"
          >
            <Plus size={18} className="text-accent" />
            <span className="text-sm font-semibold">Create your first project</span>
          </button>
        ) : (
          <div className="grid grid-cols-3 gap-4">
            {recentProjects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                onClick={() => navigate(`/workspaces/${workspace.id}/projects/${project.id}`)}
              />
            ))}
          </div>
        )}
      </div>

      {showCreateWorkspace && (
        <Modal onClose={() => (creatingWorkspace ? null : setShowCreateWorkspace(false))}>
          <h3 className="mb-6 pr-6 text-lg font-bold text-text">Create Workspace</h3>
          <form onSubmit={handleCreateWorkspace} className="flex flex-col gap-4">
            <div>
              <label className="mb-1 block text-sm font-semibold text-text">Workspace name</label>
              <input
                type="text"
                value={newWorkspaceName}
                onChange={(e) => setNewWorkspaceName(e.target.value)}
                placeholder="e.g. MIT Research Lab"
                className="w-full rounded-lg border border-border px-3.5 py-2 text-sm"
              />
            </div>
            {error && <ErrorBanner message={error} />}
            <div className="mt-2 flex gap-2.5">
              <button
                type="button"
                onClick={() => setShowCreateWorkspace(false)}
                disabled={creatingWorkspace}
                className="btn-secondary flex-1 py-2.5"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!newWorkspaceName.trim() || creatingWorkspace}
                className="btn-primary flex-1 py-2.5"
              >
                {creatingWorkspace ? "Creating..." : "Create Workspace"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </AppShell>
  );
}
