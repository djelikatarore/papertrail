import { Download, FileText, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import AppShell from "../components/AppShell";
import ErrorBanner from "../components/ErrorBanner";
import PaperCard from "../components/PaperCard";
import { downloadDraftPdf, generateDraft } from "../services/draftService";
import { listProjectPapers } from "../services/paperService";
import { DOCUMENT_TYPE_LABELS, DOCUMENT_TYPES } from "../utils/documentTypes";

// The generation prompt always asks the model for "## Section Name" Markdown
// headers (see backend/app/services/draft_generation_service.py::
// _build_draft_prompt) — splitting on that real structure lets the result
// render as one card per section like the Figma reference, without inventing
// any section data that isn't actually in draft.content.
function splitIntoSections(content) {
  if (!content) return [];
  const matches = [...content.matchAll(/^##\s+(.+)$/gm)];
  if (matches.length === 0) return [{ title: null, body: content.trim() }];

  return matches.map((match, i) => {
    const start = match.index + match[0].length;
    const end = i + 1 < matches.length ? matches[i + 1].index : content.length;
    return { title: match[1].trim(), body: content.slice(start, end).trim() };
  });
}

export default function DraftGenerationPage() {
  const { workspaceId, projectId } = useParams();
  const navigate = useNavigate();

  const [papers, setPapers] = useState([]);
  const [loadingPapers, setLoadingPapers] = useState(true);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [documentType, setDocumentType] = useState(DOCUMENT_TYPES[0]);

  const [generating, setGenerating] = useState(false);
  const [draft, setDraft] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    listProjectPapers(workspaceId, projectId, { limit: 100 })
      .then((res) => setPapers(res.items))
      .catch(() => setError("Could not load papers for this project."))
      .finally(() => setLoadingPapers(false));
  }, [workspaceId, projectId]);

  const readyPapers = papers.filter((p) => p.status === "READY");
  const notReadyCount = papers.length - readyPapers.length;

  function toggle(paperId) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(paperId) ? next.delete(paperId) : next.add(paperId);
      return next;
    });
  }

  async function handleGenerate() {
    if (selectedIds.size === 0 || generating) return;
    setGenerating(true);
    setError(null);
    setDraft(null);
    try {
      const res = await generateDraft(workspaceId, projectId, {
        documentType,
        paperIds: [...selectedIds],
      });
      if (!res.generated) {
        setError(res.error ?? "The draft could not be generated. Please try again.");
      } else {
        setDraft(res.draft);
      }
    } catch (err) {
      setError(err.response?.data?.detail ?? "Could not generate this draft. Please try again.");
    } finally {
      setGenerating(false);
    }
  }

  const sections = draft ? splitIntoSections(draft.content) : [];

  return (
    <AppShell
      workspaceId={workspaceId}
      title="Draft Generation"
      subtitle="Generate a structured draft from your project's papers"
      onBack={() => navigate(`/workspaces/${workspaceId}/projects/${projectId}`)}
    >
      <div className="grid grid-cols-1 gap-6 p-10 md:grid-cols-[260px_1fr]">
        <div className="h-fit rounded-card border border-border bg-card p-5 shadow-card md:sticky md:top-5">
          <p className="mb-3.5 text-sm font-bold text-text">Document type</p>
          <select
            value={documentType}
            onChange={(e) => setDocumentType(e.target.value)}
            aria-label="Document type"
            className="mb-5 w-full rounded-lg border border-border px-3 py-1.5 text-sm text-text"
          >
            {DOCUMENT_TYPES.map((type) => (
              <option key={type} value={type}>
                {DOCUMENT_TYPE_LABELS[type]}
              </option>
            ))}
          </select>

          <p className="mb-3.5 text-sm font-bold text-text">Select papers</p>
          {loadingPapers ? (
            <p className="text-xs text-muted">Loading papers...</p>
          ) : readyPapers.length === 0 ? (
            <p className="text-xs text-muted">
              No papers are ready yet. Upload and wait for processing to finish before generating a
              draft.
            </p>
          ) : (
            <div className="flex flex-col gap-2" role="group" aria-label="Select papers to include">
              {readyPapers.map((paper) => (
                <PaperCard
                  key={paper.id}
                  paper={paper}
                  selected={selectedIds.has(paper.id)}
                  onClick={() => toggle(paper.id)}
                />
              ))}
            </div>
          )}
          {notReadyCount > 0 && (
            <p className="mt-2.5 text-xs text-muted">
              {notReadyCount} paper{notReadyCount > 1 ? "s are" : " is"} still processing and can't be
              included yet.
            </p>
          )}

          <button
            type="button"
            onClick={handleGenerate}
            disabled={selectedIds.size === 0 || generating}
            className="mt-5 flex w-full items-center justify-center gap-1.5 rounded-lg bg-accent py-2.5 text-sm font-semibold text-white disabled:opacity-40"
          >
            <Sparkles size={14} /> {generating ? "Generating..." : "Generate Draft"}
          </button>
          {selectedIds.size > 0 && (
            <p className="mt-2 text-center text-xs text-muted">
              {selectedIds.size} paper{selectedIds.size > 1 ? "s" : ""} selected
            </p>
          )}
        </div>

        <div>
          {error && (
            <div className="mb-5">
              <ErrorBanner message={error} />
            </div>
          )}

          {!draft && !generating && (
            <div className="py-20 text-center text-muted">
              <Sparkles size={40} strokeWidth={1} className="mx-auto mb-3 text-border" />
              <p className="mb-1 text-[15px] font-semibold text-text">Ready to generate</p>
              <p className="text-[13px]">Select papers and click Generate to create your draft</p>
            </div>
          )}

          {generating && (
            <div className="py-20 text-center">
              <div
                role="status"
                aria-label="Generating draft"
                className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-[3px] border-accent-light border-t-accent"
              />
              <p className="text-sm text-muted">Generating your draft...</p>
            </div>
          )}

          {draft && !generating && (
            <div className="flex flex-col gap-4">
              <div className="rounded-card border border-border bg-card p-5 shadow-card">
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <h2 className="text-lg font-bold text-text">{draft.title}</h2>
                  <div className="flex shrink-0 flex-wrap items-center gap-1.5">
                    <span className="rounded-full bg-accent-light px-2 py-0.5 text-[11px] font-semibold text-accent">
                      {DOCUMENT_TYPE_LABELS[draft.document_type] ?? draft.document_type}
                    </span>
                    <span className="rounded-full bg-border px-2 py-0.5 text-[11px] font-semibold text-muted">
                      v{draft.version}
                    </span>
                  </div>
                </div>

                {draft.pdf_path && (
                  <div className="mt-3 flex items-center justify-between rounded-lg bg-app-bg px-3.5 py-2.5">
                    <div className="flex items-center gap-2 text-xs text-muted">
                      <FileText size={14} /> PDF generated from this draft
                    </div>
                    <button
                      type="button"
                      onClick={() => downloadDraftPdf(workspaceId, projectId, draft)}
                      className="flex items-center gap-1.5 rounded-md bg-accent px-3 py-1.5 text-xs font-semibold text-white"
                    >
                      <Download size={12} /> Download PDF
                    </button>
                  </div>
                )}
              </div>

              {sections.map((section, i) => (
                <div key={i} className="overflow-hidden rounded-card border border-border bg-card">
                  {section.title && (
                    <div className="border-b border-border px-5 py-3.5">
                      <h3 className="text-sm font-bold text-text">{section.title}</h3>
                    </div>
                  )}
                  <div className="whitespace-pre-wrap px-5 py-4 text-[13.5px] leading-relaxed text-text">
                    {section.body}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
