import { Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import AppShell from "../components/AppShell";
import ErrorBanner from "../components/ErrorBanner";
import PaginationControls from "../components/PaginationControls";
import ProjectCard from "../components/ProjectCard";
import { createProject } from "../services/projectService";
import { listProjects } from "../services/workspaceService";

export default function WorkspacePage() {
  const { workspaceId } = useParams();
  const navigate = useNavigate();

  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newTopic, setNewTopic] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    load(page);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  function load(targetPage) {
    setLoading(true);
    setError(null);
    listProjects(workspaceId, { page: targetPage, limit: 9 })
      .then((res) => {
        setItems(res.items);
        setTotalPages(res.total_pages);
        setTotal(res.total);
      })
      .catch(() => setError("Could not load projects. Please try again."))
      .finally(() => setLoading(false));
  }

  async function handleCreate(event) {
    event.preventDefault();
    if (!newTitle.trim() || !newTopic.trim() || creating) return;
    setCreating(true);
    try {
      await createProject(workspaceId, { title: newTitle.trim(), topic: newTopic.trim() });
      setShowModal(false);
      setNewTitle("");
      setNewTopic("");
      load(1);
      setPage(1);
    } catch {
      setError("Could not create project. Please try again.");
    } finally {
      setCreating(false);
    }
  }

  return (
    <AppShell workspaceId={workspaceId} title="Projects">
      <div className="p-10">
        <div className="mb-7 flex items-center justify-between">
          <p className="text-sm text-muted">{total} projects · Organize papers by research topic</p>
          <button
            type="button"
            onClick={() => setShowModal(true)}
            className="flex items-center gap-1.5 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white"
          >
            <Plus size={15} /> New Project
          </button>
        </div>

        {error && (
          <div className="mb-6">
            <ErrorBanner message={error} />
          </div>
        )}

        {!loading && (
          <div className="grid grid-cols-3 gap-4">
            {items.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                onClick={() => navigate(`/workspaces/${workspaceId}/projects/${project.id}`)}
              />
            ))}
            <button
              type="button"
              onClick={() => setShowModal(true)}
              className="flex min-h-40 flex-col items-center justify-center gap-2.5 rounded-card border-2 border-dashed border-border"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent-light">
                <Plus size={18} className="text-accent" />
              </div>
              <p className="text-sm font-semibold text-muted">Create new project</p>
            </button>
          </div>
        )}

        <PaginationControls page={page} totalPages={totalPages} onPageChange={setPage} />
      </div>

      {showModal && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-text/40">
          <div className="w-full max-w-md rounded-card bg-card p-8 shadow-card-hover">
            <h3 className="mb-6 text-lg font-bold text-text">New Project</h3>
            <form onSubmit={handleCreate} className="flex flex-col gap-4">
              <div>
                <label className="mb-1 block text-sm font-semibold text-text">Project name</label>
                <input
                  type="text"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="e.g. Transformer Architectures"
                  className="w-full rounded-lg border border-border px-3.5 py-2 text-sm"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-semibold text-text">Research topic</label>
                <input
                  type="text"
                  value={newTopic}
                  onChange={(e) => setNewTopic(e.target.value)}
                  placeholder="e.g. Self-attention mechanisms"
                  className="w-full rounded-lg border border-border px-3.5 py-2 text-sm"
                />
              </div>
              <div className="mt-2 flex gap-2.5">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 rounded-lg border border-border py-2.5 text-sm font-semibold text-text"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!newTitle.trim() || !newTopic.trim() || creating}
                  className="flex-1 rounded-lg bg-accent py-2.5 text-sm font-semibold text-white disabled:opacity-40"
                >
                  Create Project
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AppShell>
  );
}
