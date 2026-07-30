import { PenTool, Sparkles, Upload } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import AppShell from "../components/AppShell";
import ErrorBanner from "../components/ErrorBanner";
import SuggestionCard from "../components/SuggestionCard";
import {
  listDrafts,
  listReviewComments,
  submitDraftFeedback,
  updateReviewComment,
} from "../services/draftService";
import { DOCUMENT_TYPE_LABELS } from "../utils/documentTypes";

export default function DraftReviewPage() {
  const { workspaceId, projectId } = useParams();
  const navigate = useNavigate();

  const [drafts, setDrafts] = useState([]);
  const [loadingDrafts, setLoadingDrafts] = useState(true);
  const [selectedDraft, setSelectedDraft] = useState(null);

  const [comments, setComments] = useState([]);
  const [loadingComments, setLoadingComments] = useState(false);

  const [feedbackMode, setFeedbackMode] = useState("text");
  const [feedbackText, setFeedbackText] = useState("");
  const [feedbackFile, setFeedbackFile] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [discardedCount, setDiscardedCount] = useState(0);
  const [error, setError] = useState(null);

  useEffect(() => {
    listDrafts(workspaceId, projectId)
      .then(setDrafts)
      .catch(() => setError("Could not load drafts. Please try again."))
      .finally(() => setLoadingDrafts(false));
  }, [workspaceId, projectId]);

  function selectDraft(draft) {
    setSelectedDraft(draft);
    setError(null);
    setDiscardedCount(0);
    setFeedbackText("");
    setFeedbackFile(null);
    setFeedbackMode("text");
    setLoadingComments(true);
    listReviewComments(workspaceId, projectId, draft.id)
      .then(setComments)
      .catch(() => setError("Could not load review comments for this draft."))
      .finally(() => setLoadingComments(false));
  }

  const canAnalyze =
    feedbackMode === "text" ? feedbackText.trim().length > 0 : feedbackFile != null;

  async function handleAnalyze() {
    if (!canAnalyze || analyzing) return;
    setAnalyzing(true);
    setError(null);
    try {
      const res = await submitDraftFeedback(workspaceId, projectId, selectedDraft.id, {
        feedbackText: feedbackMode === "text" ? feedbackText.trim() : undefined,
        feedbackFile: feedbackMode === "file" ? feedbackFile : undefined,
      });
      setComments((prev) => [...prev, ...res.comments]);
      setDiscardedCount(res.discarded_count);
    } catch (err) {
      setError(err.response?.data?.detail ?? "Could not analyze this feedback. Please try again.");
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleStatusChange(comment, status) {
    const previous = comments;
    setComments((prev) => prev.map((c) => (c.id === comment.id ? { ...c, status } : c)));
    try {
      await updateReviewComment(workspaceId, projectId, selectedDraft.id, comment.id, { status });
    } catch {
      setComments(previous);
      setError("Could not update this suggestion. Please try again.");
    }
  }

  const pending = comments.filter((c) => c.status === "OPEN").length;
  const accepted = comments.filter((c) => c.status === "ACCEPTED").length;
  const dismissed = comments.filter((c) => c.status === "DISMISSED").length;

  if (!selectedDraft) {
    return (
      <AppShell
        workspaceId={workspaceId}
        title="Draft Review"
        subtitle="Select a draft to review"
        onBack={() => navigate(`/workspaces/${workspaceId}/projects/${projectId}`)}
      >
        <div className="p-10">
          {error && (
            <div className="mb-6">
              <ErrorBanner message={error} />
            </div>
          )}
          {!loadingDrafts && drafts.length === 0 && (
            <p className="text-sm text-muted">
              No drafts exist in this project yet. Generate one first from Draft Generation.
            </p>
          )}
          <div className="flex flex-col gap-2.5">
            {drafts.map((draft) => (
              <button
                key={draft.id}
                type="button"
                onClick={() => selectDraft(draft)}
                className="flex items-center justify-between rounded-card border border-border bg-card p-4 text-left shadow-card hover:shadow-card-hover"
              >
                <div>
                  <p className="text-sm font-semibold text-text">{draft.title}</p>
                  <p className="mt-0.5 text-xs text-muted">
                    {DOCUMENT_TYPE_LABELS[draft.document_type] ?? draft.document_type} · v{draft.version}
                  </p>
                </div>
                <span className="rounded-full bg-accent-light px-2 py-0.5 text-[11px] font-semibold text-accent">
                  {draft.status}
                </span>
              </button>
            ))}
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell
      workspaceId={workspaceId}
      title="Draft Review"
      subtitle={selectedDraft.title}
      onBack={() => setSelectedDraft(null)}
    >
      <div className="grid grid-cols-2 items-start gap-6 p-10">
        <div>
          {error && (
            <div className="mb-4">
              <ErrorBanner message={error} />
            </div>
          )}

          <div className="mb-4 overflow-hidden rounded-card border border-border bg-card">
            <div className="border-b border-border px-5 py-3.5">
              <p className="text-sm font-bold text-text">Draft Content</p>
            </div>
            <div className="max-h-64 overflow-auto whitespace-pre-wrap px-5 py-4 text-[13.5px] leading-relaxed text-text">
              {selectedDraft.content ?? "This draft has no content yet."}
            </div>
          </div>

          <div className="mb-4 overflow-hidden rounded-card border border-border bg-card">
            <div className="flex items-center justify-between border-b border-border px-5 py-3.5">
              <p className="text-sm font-bold text-text">Reviewer Feedback</p>
              <div className="flex gap-1 rounded-lg bg-app-bg p-0.5">
                <button
                  type="button"
                  onClick={() => setFeedbackMode("text")}
                  className={`rounded-md px-2.5 py-1 text-xs font-semibold ${
                    feedbackMode === "text" ? "bg-card text-accent shadow-card" : "text-muted"
                  }`}
                >
                  Paste text
                </button>
                <button
                  type="button"
                  onClick={() => setFeedbackMode("file")}
                  className={`rounded-md px-2.5 py-1 text-xs font-semibold ${
                    feedbackMode === "file" ? "bg-card text-accent shadow-card" : "text-muted"
                  }`}
                >
                  Upload file
                </button>
              </div>
            </div>
            {feedbackMode === "text" ? (
              <textarea
                value={feedbackText}
                onChange={(e) => setFeedbackText(e.target.value)}
                rows={5}
                placeholder="Paste reviewer feedback about this draft…"
                className="w-full resize-y border-none px-5 py-4 text-[13.5px] leading-relaxed text-text outline-none"
              />
            ) : (
              <div className="px-5 py-4">
                <label className="flex cursor-pointer items-center justify-center gap-2 rounded-lg border-2 border-dashed border-border py-6 text-sm text-muted">
                  <Upload size={16} />
                  {feedbackFile ? feedbackFile.name : "Choose a text file"}
                  <input
                    type="file"
                    accept=".txt,text/plain"
                    className="hidden"
                    onChange={(e) => setFeedbackFile(e.target.files?.[0] ?? null)}
                  />
                </label>
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={handleAnalyze}
            disabled={!canAnalyze || analyzing}
            className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-accent py-2.5 text-sm font-semibold text-white disabled:opacity-40"
          >
            <Sparkles size={14} /> {analyzing ? "Analyzing..." : "Analyze with AI"}
          </button>

          {discardedCount > 0 && (
            <p className="mt-2.5 text-xs text-muted">
              {discardedCount} suggestion{discardedCount > 1 ? "s" : ""} could not be verified against
              your feedback and {discardedCount > 1 ? "were" : "was"} discarded.
            </p>
          )}
        </div>

        <div>
          {loadingComments ? (
            <p className="text-sm text-muted">Loading suggestions...</p>
          ) : comments.length === 0 ? (
            <div className="py-20 text-center text-muted">
              <PenTool size={36} strokeWidth={1} className="mx-auto mb-3 text-border" />
              <p className="mb-1 text-sm font-semibold text-text">No suggestions yet</p>
              <p className="text-[13px]">Add reviewer feedback and click Analyze</p>
            </div>
          ) : (
            <>
              <div className="mb-4 flex items-center justify-between">
                <p className="text-sm font-bold text-text">{comments.length} suggestions</p>
                <div className="flex gap-2">
                  {pending > 0 && (
                    <span className="rounded-full bg-amber-light px-2 py-0.5 text-[11px] font-semibold text-amber">
                      {pending} pending
                    </span>
                  )}
                  {accepted > 0 && (
                    <span className="rounded-full bg-green-light px-2 py-0.5 text-[11px] font-semibold text-green">
                      {accepted} accepted
                    </span>
                  )}
                  {dismissed > 0 && (
                    <span className="rounded-full bg-border px-2 py-0.5 text-[11px] font-semibold text-muted">
                      {dismissed} dismissed
                    </span>
                  )}
                </div>
              </div>
              <div className="flex flex-col gap-3">
                {comments.map((comment) => (
                  <SuggestionCard
                    key={comment.id}
                    comment={comment}
                    onAccept={(c) => handleStatusChange(c, "ACCEPTED")}
                    onDismiss={(c) => handleStatusChange(c, "DISMISSED")}
                  />
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </AppShell>
  );
}
