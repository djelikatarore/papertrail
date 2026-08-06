import { Download, MessageSquare, Search, Send, Sparkles, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import AppShell from "../components/AppShell";
import AuthenticatedImage from "../components/AuthenticatedImage";
import ConfirmDeleteModal from "../components/ConfirmDeleteModal";
import ErrorBanner from "../components/ErrorBanner";
import NonAcademicWarningBanner from "../components/NonAcademicWarningBanner";
import NonAcademicWarningModal from "../components/NonAcademicWarningModal";
import PaperTypeBadge from "../components/PaperTypeBadge";
import ReviewTypeBadge from "../components/ReviewTypeBadge";
import SimilarityPanel from "../components/SimilarityPanel";
import { StatusPill } from "../components/StatusBadge";
import { askQuestion, deletePaper, downloadPaperPdf, getPaper, getPaperChatHistory } from "../services/paperService";
import { getProject, getSimilarity } from "../services/projectService";
import { listWorkspaces } from "../services/workspaceService";

const SUMMARY_TABS = [
  { key: "contribution", label: "Summary" },
  { key: "methodology", label: "Methodology" },
  { key: "key_results", label: "Key Results" },
  { key: "limitations", label: "Limitations" },
];

// Chat history only stores role/content (no cited_section/refused — those
// only exist on a live ask() response), and always saves messages as
// user-then-assistant pairs (backend/app/services/chat_service.py::
// save_exchange) in a single flat, date-sorted, id-ordered list — so pairing
// consecutive user/assistant messages back into exchanges is safe and loses
// nothing that was actually there.
function chatHistoryToExchanges(history) {
  const messages = history.flatMap((group) => group.messages);
  const exchanges = [];
  for (let i = 0; i < messages.length; i++) {
    if (messages[i].role !== "user") continue;
    const next = messages[i + 1];
    exchanges.push({
      question: messages[i].content,
      answer: next?.role === "assistant" ? next.content : "",
      cited_section: null,
      refused: false,
    });
  }
  return exchanges;
}

export default function PaperDetailsPage() {
  const { workspaceId, projectId, paperId } = useParams();
  const navigate = useNavigate();

  const [paper, setPaper] = useState(null);
  const [project, setProject] = useState(null);
  const [similarPapers, setSimilarPapers] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const [showQa, setShowQa] = useState(false);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [qaError, setQaError] = useState(null);
  const [exchanges, setExchanges] = useState([]);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState(null);
  const [summaryTab, setSummaryTab] = useState(SUMMARY_TABS[0].key);
  const [isOwner, setIsOwner] = useState(false);
  const [ownerCheckFailed, setOwnerCheckFailed] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState(null);
  const [showWarningModal, setShowWarningModal] = useState(false);
  const [warningDeleting, setWarningDeleting] = useState(false);
  const [warningDeleteError, setWarningDeleteError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      getPaper(paperId),
      getProject(workspaceId, projectId),
      getSimilarity(workspaceId, projectId).catch(() => []),
      getPaperChatHistory(paperId).catch(() => []),
    ])
      .then(([paperData, projectData, similarityData, chatHistory]) => {
        setPaper(paperData);
        setProject(projectData);
        const mine = similarityData.find((s) => s.paper_id === Number(paperId));
        setSimilarPapers(mine?.similar_papers ?? []);
        setExchanges(chatHistoryToExchanges(chatHistory));
      })
      .catch(() => setError("Could not load this paper. Please try again."))
      .finally(() => setLoading(false));
    setOwnerCheckFailed(false);
    listWorkspaces()
      .then((workspaces) => {
        const current = workspaces.find((w) => w.id === Number(workspaceId));
        setIsOwner(current?.role === "OWNER");
      })
      .catch(() => setOwnerCheckFailed(true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceId, projectId, paperId]);

  // Shown once per paper — "Keep it anyway" (or the modal's own close button)
  // marks it seen in localStorage so it doesn't nag again on a later visit.
  // Owner-only: the modal's real choice is "delete or not", which a
  // non-owner can't do anyway (same gating as the Trash2 button below).
  useEffect(() => {
    if (!paper?.content_warning || !isOwner) return;
    if (localStorage.getItem(`paperWarningSeen_${paperId}`) === "true") return;
    setShowWarningModal(true);
  }, [paper, isOwner, paperId]);

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
      >
        <div className="p-10">
          <ErrorBanner message={error ?? "Paper not found."} />
        </div>
      </AppShell>
    );
  }

  const displayTitle = paper.title ?? paper.filename;

  async function handleDownload() {
    if (downloading) return;
    setDownloading(true);
    setDownloadError(null);
    try {
      await downloadPaperPdf(paper);
    } catch {
      setDownloadError("Could not download this paper. Please try again.");
    } finally {
      setDownloading(false);
    }
  }

  async function handleDeletePaper() {
    if (deleting) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deletePaper(paperId);
      navigate(`/workspaces/${workspaceId}/projects/${projectId}`);
    } catch {
      setDeleteError("Could not delete this paper. Please try again.");
      setDeleting(false);
    }
  }

  function handleKeepWarning() {
    localStorage.setItem(`paperWarningSeen_${paperId}`, "true");
    setShowWarningModal(false);
  }

  async function handleDeleteFromWarning() {
    if (warningDeleting) return;
    setWarningDeleting(true);
    setWarningDeleteError(null);
    try {
      await deletePaper(paperId);
      navigate(`/workspaces/${workspaceId}/projects/${projectId}`);
    } catch {
      setWarningDeleteError("Could not delete this paper. Please try again.");
      setWarningDeleting(false);
    }
  }

  async function handleAsk(event) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || asking) return;
    setAsking(true);
    setQaError(null);
    try {
      const res = await askQuestion(paperId, trimmed);
      setExchanges((prev) => [...prev, { question: trimmed, ...res }]);
      setQuestion("");
    } catch (err) {
      setQaError(err.response?.data?.detail ?? "Could not get an answer. Please try again.");
    } finally {
      setAsking(false);
    }
  }

  return (
    <AppShell
      workspaceId={workspaceId}
      title={displayTitle}
    >
      <div className="p-10">
        <div className="mb-6 rounded-[var(--radius-card-lg)] border border-border bg-card p-7 shadow-card">
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

        <div className="mb-6 overflow-hidden rounded-[var(--radius-card-lg)] border border-border bg-card shadow-card">
          <div className="flex px-6 pt-1" style={{ borderBottom: "1px solid var(--color-border)" }}>
            {SUMMARY_TABS.map((tab) => (
              <button
                key={tab.key}
                type="button"
                onClick={() => setSummaryTab(tab.key)}
                className={`-mb-px border-b-2 px-4 py-3.5 text-sm font-semibold transition-colors ${
                  summaryTab === tab.key
                    ? "border-accent text-accent"
                    : "border-transparent text-muted hover:text-text"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <div className="p-7">
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-text">
              {paper[summaryTab] ?? "Not available."}
            </p>
          </div>
        </div>

        {paper.visual_elements.length > 0 && (
          <div className="mb-6 rounded-[var(--radius-card-lg)] border border-border bg-card p-6 shadow-card">
            <p className="mb-4 text-sm font-bold text-text">Figures</p>
            <div className="grid grid-cols-3 gap-4">
              {paper.visual_elements.map((ve) => (
                <div key={ve.id}>
                  <AuthenticatedImage
                    src={`/papers/${paperId}/visual-elements/${ve.id}/image`}
                    alt={ve.ai_description ?? `Figure on page ${ve.page_number}`}
                    className="mb-2 h-32 w-full rounded-xl border border-border object-cover"
                  />
                  <p className="text-xs leading-snug text-muted">
                    {ve.ai_description ?? "No description available."}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mb-6 rounded-[var(--radius-card-lg)] border border-border bg-card p-6 shadow-card">
          <p className="mb-1 text-sm font-bold text-text">Similarity</p>
          <p className="mb-4 text-xs text-muted">
            How closely this paper relates to others in the project, based on content embeddings.
          </p>
          <SimilarityPanel similarPapers={similarPapers} />
        </div>

        <div className={downloadError ? "mb-2 flex gap-2.5" : "mb-6 flex gap-2.5"}>
          <button
            type="button"
            onClick={() =>
              navigate(`/workspaces/${workspaceId}/projects/${projectId}/papers/${paperId}/similar`)
            }
            className="flex items-center gap-1.5 rounded-xl bg-accent-light px-4 py-2 text-sm font-semibold text-accent transition-colors hover:bg-accent/20"
          >
            <Search size={14} /> Similar Papers
          </button>
          <button
            type="button"
            onClick={() => setShowQa((v) => !v)}
            aria-expanded={showQa}
            className="flex items-center gap-1.5 rounded-xl bg-accent-light px-4 py-2 text-sm font-semibold text-accent transition-colors hover:bg-accent/20"
          >
            <MessageSquare size={14} /> Ask AI
          </button>
          <button
            type="button"
            onClick={handleDownload}
            disabled={downloading}
            className="btn-secondary px-4 py-2"
          >
            <Download size={14} /> {downloading ? "Downloading..." : "Download PDF"}
          </button>
          {isOwner && (
            <button
              type="button"
              onClick={() => setShowDeleteConfirm(true)}
              aria-label="Delete paper"
              className="rounded-xl border border-border p-2 text-red transition-colors hover:bg-red-light"
            >
              <Trash2 size={15} />
            </button>
          )}
        </div>

        {downloadError && (
          <div className="mb-6">
            <ErrorBanner message={downloadError} />
          </div>
        )}

        {ownerCheckFailed && (
          <div className="mb-6">
            <ErrorBanner message="Couldn't verify your permissions on this workspace — owner-only actions (like deleting this paper) may not appear until you reload the page." />
          </div>
        )}

        {showQa && (
          <div className="mb-6 overflow-hidden rounded-[var(--radius-card-lg)] border border-border bg-card shadow-card">
            <div className="border-b border-border px-6 py-4">
              <p className="text-sm font-bold text-text">Ask AI</p>
              <p className="mt-0.5 text-xs text-muted">
                Ask a question grounded in this paper's content — answers cite the section they come from.
              </p>
            </div>

            <div className="px-6 py-5">
              {exchanges.length > 0 && (
                <div className="mb-4 flex flex-col gap-3.5">
                  {exchanges.map((ex, i) => (
                    <div key={i} className="flex flex-col gap-2.5">
                      <div className="flex justify-end">
                        <div className="max-w-[80%] rounded-2xl rounded-tr-md bg-accent px-4 py-2.5 text-sm text-white">
                          {ex.question}
                        </div>
                      </div>
                      <div className="flex items-start gap-2.5">
                        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-accent">
                          <Sparkles size={13} className="text-white" strokeWidth={1.5} />
                        </div>
                        <div className="flex max-w-[80%] flex-col gap-1">
                          <div
                            className={`rounded-2xl rounded-tl-md px-4 py-2.5 text-sm leading-relaxed ${
                              ex.refused ? "border border-border text-muted italic" : "bg-app-bg text-text"
                            }`}
                          >
                            {ex.answer}
                          </div>
                          {ex.cited_section && (
                            <p className="px-1 text-xs text-muted">Source: {ex.cited_section}</p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {qaError && (
                <div className="mb-4">
                  <ErrorBanner message={qaError} />
                </div>
              )}

              <form onSubmit={handleAsk} className="flex gap-2">
                <label htmlFor="paper-question" className="sr-only">
                  Ask a question about this paper
                </label>
                <input
                  id="paper-question"
                  type="text"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="Ask a question about this paper…"
                  className="flex-1 rounded-xl border border-border px-3.5 py-2.5 text-sm text-text outline-none transition-colors focus:border-accent"
                />
                <button
                  type="submit"
                  disabled={!question.trim() || asking}
                  className="btn-primary shrink-0 px-4 py-2.5"
                >
                  <Send size={13} /> {asking ? "Asking..." : "Ask"}
                </button>
              </form>
            </div>
          </div>
        )}
      </div>

      {showDeleteConfirm && (
        <ConfirmDeleteModal
          title={`Delete "${displayTitle}"?`}
          description="This permanently deletes this paper and everything scoped to it — extracted text, figures, and its chat history. This cannot be undone."
          confirmLabel="Delete paper"
          deleting={deleting}
          error={deleteError}
          onConfirm={handleDeletePaper}
          onClose={() => setShowDeleteConfirm(false)}
        />
      )}

      {showWarningModal && (
        <NonAcademicWarningModal
          onKeep={handleKeepWarning}
          onDelete={handleDeleteFromWarning}
          deleting={warningDeleting}
          error={warningDeleteError}
        />
      )}
    </AppShell>
  );
}
