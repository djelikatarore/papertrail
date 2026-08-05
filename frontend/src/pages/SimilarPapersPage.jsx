import { BookMarked } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import AppShell from "../components/AppShell";
import ErrorBanner from "../components/ErrorBanner";
import SimilarityRing from "../components/SimilarityRing";
import { getPaper } from "../services/paperService";
import { getSimilarity } from "../services/projectService";

export default function SimilarPapersPage() {
  const { workspaceId, projectId, paperId } = useParams();
  const navigate = useNavigate();

  const [paper, setPaper] = useState(null);
  const [similarPapers, setSimilarPapers] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([getPaper(paperId), getSimilarity(workspaceId, projectId)])
      .then(([paperData, similarityData]) => {
        setPaper(paperData);
        const mine = similarityData.find((s) => s.paper_id === Number(paperId));
        const sorted = [...(mine?.similar_papers ?? [])].sort((a, b) => b.similarity - a.similarity);
        setSimilarPapers(sorted);
      })
      .catch(() => setError("Could not load similar papers. Please try again."))
      .finally(() => setLoading(false));
  }, [workspaceId, projectId, paperId]);

  if (loading) {
    return (
      <AppShell workspaceId={workspaceId} title="Similar Papers">
        <div className="p-10 text-sm text-muted">Loading...</div>
      </AppShell>
    );
  }

  if (error || !paper) {
    return (
      <AppShell workspaceId={workspaceId} title="Similar Papers">
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
      title="Similar Papers"
      subtitle="Content similarity ranking within this project"
    >
      <div className="p-10">
        <div className="mb-5 flex items-center gap-3 rounded-2xl border border-accent/20 bg-accent-light px-4 py-3.5">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-accent">
            <BookMarked size={15} className="text-white" strokeWidth={1.5} />
          </div>
          <p className="text-sm text-accent-dark">
            <span className="font-medium text-accent">Source paper</span> · <strong>{displayTitle}</strong>
          </p>
        </div>

        {similarPapers.length === 0 ? (
          <div className="py-16 text-center text-muted">
            <p className="font-semibold">No similar papers found in this project</p>
            <p className="mt-1 text-sm">
              Upload more papers to this project to see how they relate to each other.
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {similarPapers.map((sp, i) => {
              const pct = Math.round(sp.similarity * 100);
              return (
                <button
                  key={sp.paper_id}
                  type="button"
                  onClick={() =>
                    navigate(`/workspaces/${workspaceId}/projects/${projectId}/papers/${sp.paper_id}`)
                  }
                  className="flex items-center gap-5 rounded-[var(--radius-card-lg)] border border-border bg-card p-5 text-left shadow-card transition-shadow hover:shadow-card-hover"
                >
                  <SimilarityRing percentage={pct} />
                  <div className="min-w-0 flex-1">
                    <span className="text-xs font-mono text-muted">#{i + 1}</span>
                    <p className="truncate text-sm font-semibold text-text">
                      {sp.title ?? sp.filename}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </AppShell>
  );
}
