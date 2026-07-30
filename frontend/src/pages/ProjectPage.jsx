import { FileText, PenTool, Search, Sparkles, Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import AppShell from "../components/AppShell";
import ErrorBanner from "../components/ErrorBanner";
import ManageAccessPanel from "../components/ManageAccessPanel";
import PaginationControls from "../components/PaginationControls";
import PaperCard from "../components/PaperCard";
import UploadModal from "../components/UploadModal";
import { listProjectPapers } from "../services/paperService";
import { getProject } from "../services/projectService";
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

  const [project, setProject] = useState(null);
  const [isOwner, setIsOwner] = useState(false);
  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("ALL");
  const [showUpload, setShowUpload] = useState(false);
  const [showAccess, setShowAccess] = useState(false);
  const pollRef = useRef(null);

  useEffect(() => {
    getProject(workspaceId, projectId).then(setProject).catch(() => {});
    listWorkspaces()
      .then((workspaces) => {
        const current = workspaces.find((w) => w.id === Number(workspaceId));
        setIsOwner(current?.role === "OWNER");
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceId, projectId]);

  useEffect(() => {
    load(page);
    return () => clearInterval(pollRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, workspaceId, projectId]);

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
      onBack={() => navigate(`/workspaces/${workspaceId}`)}
    >
      <div className="p-10">
        <div className="mb-4 flex items-center justify-between">
          <div />
          <div className="flex gap-2.5">
            <button
              type="button"
              onClick={() => navigate(`/workspaces/${workspaceId}/projects/${projectId}/search`)}
              className="flex items-center gap-1.5 rounded-lg border border-border px-4 py-2 text-sm font-semibold text-text"
            >
              <Search size={15} /> Find papers
            </button>
            <button
              type="button"
              onClick={() => navigate(`/workspaces/${workspaceId}/projects/${projectId}/drafts/review`)}
              className="flex items-center gap-1.5 rounded-lg border border-border px-4 py-2 text-sm font-semibold text-text"
            >
              <PenTool size={15} /> Review drafts
            </button>
            <button
              type="button"
              onClick={() => navigate(`/workspaces/${workspaceId}/projects/${projectId}/drafts/generate`)}
              className="flex items-center gap-1.5 rounded-lg border border-border px-4 py-2 text-sm font-semibold text-text"
            >
              <Sparkles size={15} /> Generate draft
            </button>
            {isOwner && (
              <button
                type="button"
                onClick={() => setShowAccess(true)}
                className="rounded-lg border border-border px-4 py-2 text-sm font-semibold text-text"
              >
                Manage access
              </button>
            )}
            <button
              type="button"
              onClick={() => setShowUpload(true)}
              className="flex items-center gap-1.5 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white"
            >
              <Upload size={15} /> Upload to project
            </button>
          </div>
        </div>

        <div className="mb-6 flex flex-wrap gap-2">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              type="button"
              onClick={() => setFilter(f.value)}
              className={`rounded-full px-3.5 py-1 text-xs font-semibold transition-colors ${
                filter === f.value ? "bg-accent text-white" : "bg-accent-light text-accent"
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
    </AppShell>
  );
}
