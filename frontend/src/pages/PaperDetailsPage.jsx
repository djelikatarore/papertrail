import { MessageSquare, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import AppShell from "../components/AppShell";
import AuthenticatedImage from "../components/AuthenticatedImage";
import ErrorBanner from "../components/ErrorBanner";
import NonAcademicWarningBanner from "../components/NonAcademicWarningBanner";
import PaperTypeBadge from "../components/PaperTypeBadge";
import ReviewTypeBadge from "../components/ReviewTypeBadge";
import SimilarityPanel from "../components/SimilarityPanel";
import { StatusPill } from "../components/StatusBadge";
import { getPaper } from "../services/paperService";
import { getProject, getSimilarity } from "../services/projectService";

const SUMMARY_BLOCKS = [
  { key: "contribution", label: "Contribution", accent: "text-accent" },
  { key: "methodology", label: "Methodology", accent: "text-teal" },
  { key: "key_results", label: "Key Results", accent: "text-green" },
  { key: "limitations", label: "Limitations", accent: "text-amber", warning: true },
];

export default function PaperDetailsPage() {
  const { workspaceId, projectId, paperId } = useParams();
  const navigate = useNavigate();

  const [paper, setPaper] = useState(null);
  const [project, setProject] = useState(null);
  const [similarPapers, setSimilarPapers] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      getPaper(paperId),
      getProject(workspaceId, projectId),
      getSimilarity(workspaceId, projectId).catch(() => []),
    ])
      .then(([paperData, projectData, similarityData]) => {
        setPaper(paperData);
        setProject(projectData);
        const mine = similarityData.find((s) => s.paper_id === Number(paperId));
        setSimilarPapers(mine?.similar_papers ?? []);
      })
      .catch(() => setError("Could not load this paper. Please try again."))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceId, projectId, paperId]);

  if (loading) {
    return (
      <AppShell workspaceId={workspaceId} title="Paper Details">
        <div className="p-10 text-sm text-muted">Loading...</div>
      </AppShell>
    );
  }

  if (error || !paper) {
    return (
      <AppShell
        workspaceId={workspaceId}
        title="Paper Details"
        onBack={() => navigate(`/workspaces/${workspaceId}/projects/${projectId}`)}
      >
        <div className="p-10">
          <ErrorBanner message={error ?? "Paper not found."} />
        </div>
      </AppShell>
    );
  }

  const displayTitle = paper.title ?? paper.filename;

  return (
    <AppShell
      workspaceId={workspaceId}
      title={displayTitle}
      onBack={() => navigate(`/workspaces/${workspaceId}/projects/${projectId}`)}
    >
      <div className="p-10">
        <div className="mb-7">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            {project && (
              <span className="rounded-full bg-accent-light px-2.5 py-0.5 text-[11px] font-semibold text-accent">
                {project.title}
              </span>
            )}
            <StatusPill status={paper.status} />
            <ReviewTypeBadge reviewType={paper.review_type} />
            <PaperTypeBadge detectedPaperType={paper.detected_paper_type} />
          </div>
          <p className="text-sm text-muted">
            {paper.page_count != null ? `${paper.page_count} pages` : ""}
            {paper.upload_date ? ` · Uploaded ${new Date(paper.upload_date).toLocaleDateString()}` : ""}
          </p>
        </div>

        {paper.content_warning && (
          <div className="mb-6">
            <NonAcademicWarningBanner contentWarning={paper.content_warning} />
          </div>
        )}

        <div className="mb-7 grid grid-cols-2 gap-3.5">
          {SUMMARY_BLOCKS.map((block) => (
            <div
              key={block.key}
              className={`rounded-card border p-5 ${
                block.warning ? "border-amber/20 bg-amber-light" : "border-border bg-card"
              }`}
            >
              <p className={`mb-2 text-[11px] font-bold uppercase tracking-wide ${block.accent}`}>
                {block.label}
              </p>
              <p className="text-sm leading-relaxed text-text">
                {paper[block.key] ?? "Not available."}
              </p>
            </div>
          ))}
        </div>

        {paper.visual_elements.length > 0 && (
          <div className="mb-7 rounded-card border border-border bg-card p-6">
            <p className="mb-4 text-sm font-bold text-text">Figures</p>
            <div className="grid grid-cols-3 gap-4">
              {paper.visual_elements.map((ve) => (
                <div key={ve.id}>
                  <AuthenticatedImage
                    src={`/papers/${paperId}/visual-elements/${ve.id}/image`}
                    alt={ve.ai_description ?? `Figure on page ${ve.page_number}`}
                    className="mb-2 h-32 w-full rounded-lg border border-border object-cover"
                  />
                  <p className="text-xs leading-snug text-muted">
                    {ve.ai_description ?? "No description available."}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mb-7 rounded-card border border-border bg-card p-6">
          <p className="mb-1 text-sm font-bold text-text">Similarity</p>
          <p className="mb-4 text-xs text-muted">
            How closely this paper relates to others in the project, based on content embeddings.
          </p>
          <SimilarityPanel similarPapers={similarPapers} />
        </div>

        <div className="flex gap-2.5">
          <button
            type="button"
            disabled
            title="Coming soon"
            className="flex items-center gap-1.5 rounded-lg bg-accent-light px-4 py-2 text-sm font-semibold text-accent opacity-50"
          >
            <Search size={14} /> Similar Papers
          </button>
          <button
            type="button"
            disabled
            title="Coming soon"
            className="flex items-center gap-1.5 rounded-lg bg-accent-light px-4 py-2 text-sm font-semibold text-accent opacity-50"
          >
            <MessageSquare size={14} /> Ask AI
          </button>
        </div>
      </div>
    </AppShell>
  );
}
