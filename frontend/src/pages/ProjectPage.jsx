import { ChevronUp, FileText, MessageSquare, Network, Pencil, PenTool, Search, Sparkles, Trash2, Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import AppShell from "../components/AppShell";
import CitationGraphBarChart from "../components/CitationGraphBarChart";
import ConfirmDeleteModal from "../components/ConfirmDeleteModal";
import ErrorBanner from "../components/ErrorBanner";
import ManageAccessPanel from "../components/ManageAccessPanel";
import Modal from "../components/Modal";
import PaginationControls from "../components/PaginationControls";
import PaperCard from "../components/PaperCard";
import UploadModal from "../components/UploadModal";
import { deletePaper, listProjectPapers } from "../services/paperService";
import { deleteProject, getCitationGraph, getProject, updateProject } from "../services/projectService";
import { listWorkspaces } from "../services/workspaceService";

const FILTERS = [
  { value: "ALL", label: "All" },
  { value: "SYSTEMATIC", label: "Systematic" },
  { value: "SCOPING", label: "Scoping" },
  { value: "CRITICAL", label: "Critical" },
  { value: "NARRATIVE", label: "Narrative" },
  { value: "RAPID", label: "Rapid" },
];

export default function ProjectPage() {
  const { workspaceId, projectId } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [project, setProject] = useState(null);
  const [isOwner, setIsOwner] = useState(false);
  const [ownerCheckFailed, setOwnerCheckFailed] = useState(false);
  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("ALL");
  const [showUpload, setShowUpload] = useState(false);
  const [showAccess, setShowAccess] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editTopic, setEditTopic] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [editError, setEditError] = useState(null);
  const [paperToDelete, setPaperToDelete] = useState(null);
  const [deletingPaper, setDeletingPaper] = useState(false);
  const [deletePaperError, setDeletePaperError] = useState(null);
  const [showCitationGraph, setShowCitationGraph] = useState(false);
  const [citationGraphNodes, setCitationGraphNodes] = useState([]);
  const [citationGraphLoading, setCitationGraphLoading] = useState(false);
  const [citationGraphError, setCitationGraphError] = useState(null);
  const pollRef = useRef(null);

  async function handleDeleteProject() {
    if (deleting) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteProject(workspaceId, projectId);
      navigate(`/workspaces/${workspaceId}`);
    } catch {
      setDeleteError("Could not delete this project. Please try again.");
      setDeleting(false);
    }
  }

  async function handleDeletePaper() {
    if (deletingPaper || !paperToDelete) return;
    setDeletingPaper(true);
    setDeletePaperError(null);
    try {
      await deletePaper(paperToDelete.id);
      setItems((prev) => prev.filter((p) => p.id !== paperToDelete.id));
      setPaperToDelete(null);
    } catch {
      setDeletePaperError("Could not delete this paper. Please try again.");
    } finally {
      setDeletingPaper(false);
    }
  }

  function openEditModal() {
    setEditTitle(project?.title ?? "");
    setEditTopic(project?.topic ?? "");
    setEditDescription(project?.description ?? "");
    setEditError(null);
    setShowEditModal(true);
  }

  async function handleSaveEdit(event) {
    event.preventDefault();
    if (!editTitle.trim() || !editTopic.trim() || saving) return;
    setSaving(true);
    setEditError(null);
    try {
      const updated = await updateProject(workspaceId, projectId, {
        title: editTitle.trim(),
        topic: editTopic.trim(),
        description: editDescription.trim() || null,
      });
      setProject(updated);
      setShowEditModal(false);
    } catch {
      setEditError("Could not save these changes. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    // Navigating from one project straight to another reuses this component
    // (route params change, no remount) — without resetting here, a cached
    // graph from the PREVIOUS project could flash before the new one loads.
    setShowCitationGraph(false);
    setCitationGraphNodes([]);
    setCitationGraphError(null);
  }, [workspaceId, projectId]);

  useEffect(() => {
    getProject(workspaceId, projectId).then(setProject).catch(() => {});
    setOwnerCheckFailed(false);
    listWorkspaces()
      .then((workspaces) => {
        const current = workspaces.find((w) => w.id === Number(workspaceId));
        setIsOwner(current?.role === "OWNER");
      })
      .catch(() => setOwnerCheckFailed(true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceId, projectId]);

  useEffect(() => {
    load(page);
    return () => clearInterval(pollRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, workspaceId, projectId]);

  // The sidebar's "Upload Paper" item links here with ?upload=1 (it has no
  // upload UI of its own) so it can actually open the modal instead of just
  // dropping the user on the Library page one click short of what it promised.
  useEffect(() => {
    if (searchParams.get("upload") === "1") {
      setShowUpload(true);
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.delete("upload");
        return next;
      }, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  // Loaded lazily on first open rather than alongside the paper list — most
  // visits to this page never open the graph, so fetching it eagerly would
  // waste a request. Re-opening after the first time reuses what's already
  // loaded instead of re-fetching.
  function toggleCitationGraph() {
    if (showCitationGraph) {
      setShowCitationGraph(false);
      return;
    }
    setShowCitationGraph(true);
    if (citationGraphNodes.length > 0 || citationGraphLoading) return;
    setCitationGraphLoading(true);
    setCitationGraphError(null);
    getCitationGraph(workspaceId, projectId)
      .then((graph) => {
        setCitationGraphNodes(graph.nodes.map((n) => ({ id: n.paper_id, title: n.title, citationCount: n.citation_count })));
      })
      .catch(() => setCitationGraphError("Could not load the citation graph. Please try again."))
      .finally(() => setCitationGraphLoading(false));
  }

  function load(targetPage) {
    setLoading(true);
    setError(null);
    listProjectPapers(workspaceId, projectId, { page: targetPage, limit: 10 })
      .then((res) => {
        setItems(res.items);
        setTotalPages(res.total_pages);
        maybePoll(res.items, targetPage);
      })
      .catch(() => setError("Could not load papers. Please try again."))
      .finally(() => setLoading(false));
  }

  // While any paper on the current page is still being processed in the
  // background, poll for updates (status, figure-description progress) every
  // few seconds instead of leaving the badge stale until a manual refresh.
  // The Processing -> Ready/Error transition itself is announced by the
  // app-wide NotificationProvider (see context/NotificationContext.jsx),
  // not here — this poll only keeps this page's own list current.
  function maybePoll(currentItems, targetPage) {
    clearInterval(pollRef.current);
    const stillProcessing = currentItems.some((p) => p.status === "PROCESSING");
    if (!stillProcessing) return;

    pollRef.current = setInterval(() => {
      listProjectPapers(workspaceId, projectId, { page: targetPage, limit: 10 })
        .then((res) => {
          setItems(res.items);
          if (!res.items.some((p) => p.status === "PROCESSING")) {
            clearInterval(pollRef.current);
          }
        })
        .catch(() => clearInterval(pollRef.current));
    }, 4000);
  }

  const filtered = filter === "ALL" ? items : items.filter((p) => p.review_type === filter);

  return (
    <AppShell
      workspaceId={workspaceId}
      title={project?.title ?? "Paper Library"}
      subtitle={project?.topic}
    >
      <div className="p-10">
        <div className="mb-4 flex items-center justify-between">
          <button
            type="button"
            onClick={openEditModal}
            className="flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-xl border border-border px-3 py-1.5 text-xs font-semibold text-muted transition-colors hover:text-text"
          >
            <Pencil size={12} /> Edit project
          </button>
          <div className="flex flex-wrap justify-end gap-2.5">
            <button
              type="button"
              onClick={() => navigate(`/workspaces/${workspaceId}/projects/${projectId}/search`)}
              className="btn-secondary shrink-0 whitespace-nowrap px-4 py-2"
            >
              <Search size={15} /> Find papers
            </button>
            <button
              type="button"
              onClick={() => navigate(`/workspaces/${workspaceId}/projects/${projectId}/drafts/review`)}
              className="btn-secondary shrink-0 whitespace-nowrap px-4 py-2"
            >
              <PenTool size={15} /> Review drafts
            </button>
            <button
              type="button"
              onClick={() => navigate(`/workspaces/${workspaceId}/projects/${projectId}/drafts/generate`)}
              className="btn-secondary shrink-0 whitespace-nowrap px-4 py-2"
            >
              <Sparkles size={15} /> Generate draft
            </button>
            <button
              type="button"
              onClick={() => navigate(`/workspaces/${workspaceId}/projects/${projectId}/chat`)}
              className="btn-secondary shrink-0 whitespace-nowrap px-4 py-2"
            >
              <MessageSquare size={15} /> AI Chat
            </button>
            <button
              type="button"
              onClick={toggleCitationGraph}
              className="btn-secondary shrink-0 whitespace-nowrap px-4 py-2"
            >
              {showCitationGraph ? <ChevronUp size={15} /> : <Network size={15} />} Citation Graph
            </button>
            {isOwner && (
              <button
                type="button"
                onClick={() => setShowAccess(true)}
                className="btn-secondary shrink-0 whitespace-nowrap px-4 py-2"
              >
                Manage access
              </button>
            )}
            <button
              type="button"
              onClick={() => setShowUpload(true)}
              className="btn-primary shrink-0 whitespace-nowrap px-4 py-2"
            >
              <Upload size={15} /> Upload to project
            </button>
            {isOwner && (
              <button
                type="button"
                onClick={() => setShowDeleteConfirm(true)}
                aria-label="Delete project"
                className="shrink-0 rounded-xl border border-border p-2 text-red transition-colors hover:bg-red-light"
              >
                <Trash2 size={15} />
              </button>
            )}
          </div>
        </div>

        {project && (
          <p className="mb-4 text-xs text-muted">
            {project.created_at ? `Created ${new Date(project.created_at).toLocaleDateString()}` : ""}
            {project.created_at && project.member_count != null ? " · " : ""}
            {project.member_count != null
              ? `${project.member_count} member${project.member_count === 1 ? "" : "s"}`
              : ""}
          </p>
        )}

        {showCitationGraph && (
          <div className="mb-6 rounded-[var(--radius-card-lg)] border border-border bg-card p-6 shadow-card">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="text-sm font-bold text-text">Citation Graph — {project?.title}</p>
                <p className="text-xs text-muted">How many times each paper has been cited by other researchers</p>
              </div>
              <button
                type="button"
                onClick={() => setShowCitationGraph(false)}
                aria-label="Close citation graph"
                className="rounded-lg p-1.5 text-muted transition-colors hover:bg-app-bg hover:text-text"
              >
                <ChevronUp size={16} />
              </button>
            </div>
            {citationGraphError && <ErrorBanner message={citationGraphError} />}
            {citationGraphLoading ? (
              <p className="text-sm text-muted">Loading...</p>
            ) : (
              !citationGraphError && (
                <div className="mx-auto max-w-[640px]">
                  <CitationGraphBarChart
                    nodes={citationGraphNodes}
                    width={640}
                    height={260}
                    onNodeClick={(paperId) =>
                      navigate(`/workspaces/${workspaceId}/projects/${projectId}/papers/${paperId}`)
                    }
                  />
                </div>
              )
            )}
          </div>
        )}

        <div className="mb-6 flex flex-wrap gap-2">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              type="button"
              onClick={() => setFilter(f.value)}
              className={`rounded-full px-3.5 py-1 text-xs font-semibold transition-colors ${
                filter === f.value ? "bg-accent text-white hover:bg-accent-dark" : "bg-accent-light text-accent"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {error && (
          <div className="mb-6">
            <ErrorBanner message={error} />
          </div>
        )}

        {ownerCheckFailed && (
          <div className="mb-6">
            <ErrorBanner message="Couldn't verify your permissions on this workspace — owner-only actions (like deleting a paper or the project) may not appear until you reload the page." />
          </div>
        )}

        {!loading && filtered.length === 0 ? (
          <div className="py-16 text-center text-muted">
            <FileText size={36} strokeWidth={1} className="mx-auto mb-3 text-border" />
            <p className="font-semibold">No papers match this filter</p>
          </div>
        ) : (
          <div className="flex flex-col gap-2.5">
            {filtered.map((paper) => (
              <PaperCard
                key={paper.id}
                paper={paper}
                onClick={() =>
                  navigate(`/workspaces/${workspaceId}/projects/${projectId}/papers/${paper.id}`)
                }
                onDelete={isOwner ? setPaperToDelete : undefined}
              />
            ))}
          </div>
        )}

        <PaginationControls page={page} totalPages={totalPages} onPageChange={setPage} />
      </div>

      {showUpload && (
        <UploadModal
          workspaceId={workspaceId}
          projectId={projectId}
          onClose={() => setShowUpload(false)}
          onUploaded={() => load(page)}
        />
      )}

      {showAccess && (
        <ManageAccessPanel
          workspaceId={workspaceId}
          projectId={projectId}
          onClose={() => setShowAccess(false)}
        />
      )}

      {showEditModal && (
        <Modal onClose={() => (saving ? null : setShowEditModal(false))}>
          <h3 className="mb-6 pr-6 text-lg font-bold text-text">Edit project</h3>
          <form onSubmit={handleSaveEdit} className="flex flex-col gap-4">
            <div>
              <label className="mb-1 block text-sm font-semibold text-text">Project name</label>
              <input
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                className="w-full rounded-lg border border-border px-3.5 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-semibold text-text">Research topic</label>
              <input
                type="text"
                value={editTopic}
                onChange={(e) => setEditTopic(e.target.value)}
                className="w-full rounded-lg border border-border px-3.5 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-semibold text-text">Description</label>
              <textarea
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                rows={3}
                placeholder="Optional"
                className="w-full resize-y rounded-lg border border-border px-3.5 py-2 text-sm"
              />
            </div>
            {editError && <ErrorBanner message={editError} />}
            <div className="mt-2 flex gap-2.5">
              <button
                type="button"
                onClick={() => setShowEditModal(false)}
                disabled={saving}
                className="btn-secondary flex-1 py-2.5"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!editTitle.trim() || !editTopic.trim() || saving}
                className="btn-primary flex-1 py-2.5"
              >
                {saving ? "Saving..." : "Save changes"}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {showDeleteConfirm && (
        <ConfirmDeleteModal
          title={`Delete "${project?.title}"?`}
          description="This permanently deletes this project and everything in it — every paper, draft, review comment, and chat history. This cannot be undone."
          confirmLabel="Delete project"
          deleting={deleting}
          error={deleteError}
          onConfirm={handleDeleteProject}
          onClose={() => setShowDeleteConfirm(false)}
        />
      )}

      {paperToDelete && (
        <ConfirmDeleteModal
          title={`Delete "${paperToDelete.title ?? paperToDelete.filename}"?`}
          description="This permanently deletes this paper and everything scoped to it — extracted text, figures, and its chat history. This cannot be undone."
          confirmLabel="Delete paper"
          deleting={deletingPaper}
          error={deletePaperError}
          onConfirm={handleDeletePaper}
          onClose={() => setPaperToDelete(null)}
        />
      )}
    </AppShell>
  );
}
