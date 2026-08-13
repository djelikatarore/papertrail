import { FileText, FolderOpen, Plus, Search, Settings, UserPlus, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import AppShell from "../components/AppShell";
import ErrorBanner from "../components/ErrorBanner";
import InviteModal from "../components/InviteModal";
import Modal from "../components/Modal";
import PaginationControls from "../components/PaginationControls";
import ProjectCard from "../components/ProjectCard";
import { createProject, updateProjectStatus } from "../services/projectService";
import { listProjects, listWorkspaces, searchWorkspace } from "../services/workspaceService";

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
  const [isOwner, setIsOwner] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);

  const [searchInput, setSearchInput] = useState("");
  const [searchResults, setSearchResults] = useState(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState(null);

  useEffect(() => {
    load(page);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, workspaceId]);

  useEffect(() => {
    listWorkspaces()
      .then((workspaces) => {
        const current = workspaces.find((w) => String(w.id) === String(workspaceId));
        setIsOwner(current?.role === "OWNER");
      })
      .catch(() => setIsOwner(false));
  }, [workspaceId]);

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

  async function handleStatusChange(project, newStatus) {
    try {
      const updated = await updateProjectStatus(workspaceId, project.id, newStatus);
      setItems((prev) => prev.map((p) => (p.id === project.id ? updated : p)));
    } catch {
      setError("Could not update this project's status. Please try again.");
    }
  }

  async function handleSearch(event) {
    event.preventDefault();
    const trimmed = searchInput.trim();
    if (!trimmed || searching) return;
    setSearching(true);
    setSearchError(null);
    try {
      const res = await searchWorkspace(workspaceId, trimmed);
      setSearchResults(res);
    } catch {
      setSearchError("Could not run this search. Please try again.");
    } finally {
      setSearching(false);
    }
  }

  function clearSearch() {
    setSearchInput("");
    setSearchResults(null);
    setSearchError(null);
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
        <div className="mb-5 flex items-center justify-between">
          <p className="text-sm text-muted">{total} projects · Organize papers by research topic</p>
          <div className="flex items-center gap-2.5">
            {isOwner && (
              <button type="button" onClick={() => setShowInviteModal(true)} className="btn-secondary px-4 py-2">
                <UserPlus size={15} /> Invite
              </button>
            )}
            <button
              type="button"
              onClick={() => navigate(`/workspaces/${workspaceId}/settings`)}
              className="btn-secondary px-4 py-2"
            >
              <Settings size={15} /> Settings
            </button>
            <button type="button" onClick={() => setShowModal(true)} className="btn-primary px-4 py-2">
              <Plus size={15} /> New Project
            </button>
          </div>
        </div>

        <form onSubmit={handleSearch} className="mb-7 flex gap-2">
          <div className="relative flex-1">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search projects and papers in this workspace…"
              className="w-full rounded-xl border border-border py-2 pl-9 pr-3.5 text-sm text-text outline-none transition-colors focus:border-accent"
            />
          </div>
          {searchResults ? (
            <button type="button" onClick={clearSearch} className="btn-secondary px-4 py-2">
              <X size={14} /> Clear
            </button>
          ) : (
            <button type="submit" disabled={!searchInput.trim() || searching} className="btn-secondary px-4 py-2">
              {searching ? "Searching..." : "Search"}
            </button>
          )}
        </form>

        {error && (
          <div className="mb-6">
            <ErrorBanner message={error} />
          </div>
        )}

        {searchError && (
          <div className="mb-6">
            <ErrorBanner message={searchError} />
          </div>
        )}

        {searchResults ? (
          <div className="flex flex-col gap-6">
            <div>
              <p className="mb-2.5 text-xs font-bold uppercase tracking-wide text-muted">
                Projects ({searchResults.projects.length})
              </p>
              {searchResults.projects.length === 0 ? (
                <p className="text-sm text-muted">No matching projects.</p>
              ) : (
                <div className="flex flex-col gap-2">
                  {searchResults.projects.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => navigate(`/workspaces/${workspaceId}/projects/${p.id}`)}
                      className="flex items-center gap-2.5 rounded-2xl border border-border bg-card p-3.5 text-left shadow-card transition-shadow hover:shadow-card-hover"
                    >
                      <FolderOpen size={15} className="text-accent" />
                      <div>
                        <p className="text-sm font-semibold text-text">{p.title}</p>
                        <p className="text-xs text-muted">{p.topic}</p>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div>
              <p className="mb-2.5 text-xs font-bold uppercase tracking-wide text-muted">
                Papers ({searchResults.papers.length})
              </p>
              {searchResults.papers.length === 0 ? (
                <p className="text-sm text-muted">No matching papers.</p>
              ) : (
                <div className="flex flex-col gap-2">
                  {searchResults.papers.map((paper) => (
                    <button
                      key={paper.id}
                      type="button"
                      onClick={() =>
                        navigate(`/workspaces/${workspaceId}/projects/${paper.project_id}/papers/${paper.id}`)
                      }
                      className="flex items-center gap-2.5 rounded-2xl border border-border bg-card p-3.5 text-left shadow-card transition-shadow hover:shadow-card-hover"
                    >
                      <FileText size={15} className="text-accent" />
                      <p className="text-sm font-semibold text-text">{paper.title ?? paper.filename}</p>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : (
          <>
            {!loading && (
              <div className="grid grid-cols-3 items-start gap-4">
                {items.map((project, index) => (
                  <ProjectCard
                    key={project.id}
                    project={project}
                    index={index}
                    onClick={() => navigate(`/workspaces/${workspaceId}/projects/${project.id}`)}
                    onStatusChange={handleStatusChange}
                  />
                ))}
                <button
                  type="button"
                  onClick={() => setShowModal(true)}
                  className="flex min-h-40 flex-col items-center justify-center gap-2.5 rounded-[var(--radius-card-lg)] border-2 border-dashed border-border transition-colors hover:border-accent/40"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent-light">
                    <Plus size={18} className="text-accent" />
                  </div>
                  <p className="text-sm font-semibold text-muted">Create new project</p>
                </button>
              </div>
            )}

            <PaginationControls page={page} totalPages={totalPages} onPageChange={setPage} />
          </>
        )}
      </div>

      {showModal && (
        <Modal onClose={() => setShowModal(false)}>
          <h3 className="mb-6 pr-6 text-lg font-bold text-text">New Project</h3>
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
              <button type="button" onClick={() => setShowModal(false)} className="btn-secondary flex-1 py-2.5">
                Cancel
              </button>
              <button
                type="submit"
                disabled={!newTitle.trim() || !newTopic.trim() || creating}
                className="btn-primary flex-1 py-2.5"
              >
                Create Project
              </button>
            </div>
          </form>
        </Modal>
      )}

      {showInviteModal && (
        <InviteModal workspaceId={workspaceId} onClose={() => setShowInviteModal(false)} />
      )}
    </AppShell>
  );
}
