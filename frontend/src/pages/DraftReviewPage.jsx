import { Pencil, PenTool, Plus, Sparkles, Trash2, Upload, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import AppShell from "../components/AppShell";
import ConfirmDeleteModal from "../components/ConfirmDeleteModal";
import ErrorBanner from "../components/ErrorBanner";
import Modal from "../components/Modal";
import SuggestionCard from "../components/SuggestionCard";
import { useAuth } from "../context/AuthContext";
import {
  createDraft,
  createReviewComment,
  deleteDraft,
  deleteReviewComment,
  listDrafts,
  listReviewComments,
  submitDraftFeedback,
  updateDraft,
  updateReviewComment,
} from "../services/draftService";
import { DOCUMENT_TYPE_LABELS, DOCUMENT_TYPES } from "../utils/documentTypes";
import { splitIntoSections } from "../utils/draftSections";
import { listWorkspaces } from "../services/workspaceService";

export default function DraftReviewPage() {
  const { workspaceId, projectId } = useParams();
  const { user } = useAuth();

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

  const [editingContent, setEditingContent] = useState(false);
  const [editedContent, setEditedContent] = useState("");
  const [savingContent, setSavingContent] = useState(false);

  const [isOwner, setIsOwner] = useState(false);
  const [draftToDelete, setDraftToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState(null);

  const [noteText, setNoteText] = useState("");
  const [addingNote, setAddingNote] = useState(false);

  const [showNewDraftModal, setShowNewDraftModal] = useState(false);
  const [newDraftTitle, setNewDraftTitle] = useState("");
  const [newDraftType, setNewDraftType] = useState(DOCUMENT_TYPES[0]);
  const [newDraftContent, setNewDraftContent] = useState("");
  const [creatingDraft, setCreatingDraft] = useState(false);
  const [newDraftError, setNewDraftError] = useState(null);

  useEffect(() => {
    listDrafts(workspaceId, projectId)
      .then(setDrafts)
      .catch(() => setError("Could not load drafts. Please try again."))
      .finally(() => setLoadingDrafts(false));
    listWorkspaces()
      .then((workspaces) => {
        const current = workspaces.find((w) => w.id === Number(workspaceId));
        setIsOwner(current?.role === "OWNER");
      })
      .catch(() => {});
  }, [workspaceId, projectId]);

  async function handleDeleteDraft() {
    if (deleting || !draftToDelete) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteDraft(workspaceId, projectId, draftToDelete.id);
      setDrafts((prev) => prev.filter((d) => d.id !== draftToDelete.id));
      setDraftToDelete(null);
    } catch {
      setDeleteError("Could not delete this draft. Please try again.");
    } finally {
      setDeleting(false);
    }
  }

  function openNewDraftModal() {
    setNewDraftTitle("");
    setNewDraftType(DOCUMENT_TYPES[0]);
    setNewDraftContent("");
    setNewDraftError(null);
    setShowNewDraftModal(true);
  }

  async function handleCreateDraft(event) {
    event.preventDefault();
    if (!newDraftTitle.trim() || creatingDraft) return;
    setCreatingDraft(true);
    setNewDraftError(null);
    try {
      const draft = await createDraft(workspaceId, projectId, {
        title: newDraftTitle.trim(),
        documentType: newDraftType,
        content: newDraftContent.trim() || null,
      });
      setDrafts((prev) => [...prev, draft]);
      setShowNewDraftModal(false);
      selectDraft(draft);
    } catch {
      setNewDraftError("Could not create this draft. Please try again.");
    } finally {
      setCreatingDraft(false);
    }
  }

  async function handleDeleteComment(comment) {
    const previous = comments;
    setComments((prev) => prev.filter((c) => c.id !== comment.id));
    try {
      await deleteReviewComment(workspaceId, projectId, selectedDraft.id, comment.id);
    } catch {
      setComments(previous);
      setError("Could not delete this comment. Please try again.");
    }
  }

  async function handleAddNote(event) {
    event.preventDefault();
    const trimmed = noteText.trim();
    if (!trimmed || addingNote) return;
    setAddingNote(true);
    setError(null);
    try {
      const comment = await createReviewComment(workspaceId, projectId, selectedDraft.id, trimmed);
      setComments((prev) => [...prev, comment]);
      setNoteText("");
    } catch {
      setError("Could not add this note. Please try again.");
    } finally {
      setAddingNote(false);
    }
  }

  function selectDraft(draft) {
    setSelectedDraft(draft);
    setError(null);
    setDiscardedCount(0);
    setFeedbackText("");
    setFeedbackFile(null);
    setFeedbackMode("text");
    setEditingContent(false);
    setLoadingComments(true);
    listReviewComments(workspaceId, projectId, draft.id)
      .then(setComments)
      .catch(() => setError("Could not load review comments for this draft."))
      .finally(() => setLoadingComments(false));
  }

  function startEditingContent() {
    setEditedContent(selectedDraft.content ?? "");
    setEditingContent(true);
  }

  function cancelEditingContent() {
    setEditingContent(false);
  }

  async function saveEditedContent() {
    if (savingContent) return;
    setSavingContent(true);
    setError(null);
    try {
      const updated = await updateDraft(workspaceId, projectId, selectedDraft.id, {
        content: editedContent,
      });
      setSelectedDraft(updated);
      setDrafts((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
      setEditingContent(false);
    } catch (err) {
      setError(err.response?.data?.detail ?? "Could not save this draft. Please try again.");
    } finally {
      setSavingContent(false);
    }
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
      >
        <div className="p-10">
          <div className="mb-4 flex justify-end">
            <button type="button" onClick={openNewDraftModal} className="btn-secondary px-4 py-2">
              <Plus size={15} /> New Draft
            </button>
          </div>

          {error && (
            <div className="mb-6">
              <ErrorBanner message={error} />
            </div>
          )}
          {!loadingDrafts && drafts.length === 0 && (
            <p className="mb-4 text-sm text-muted">
              No drafts exist in this project yet. Generate one from Draft Generation, or create one manually.
            </p>
          )}
          <div className="flex flex-col gap-2.5">
            {drafts.map((draft) => (
              <button
                key={draft.id}
                type="button"
                onClick={() => selectDraft(draft)}
                className="flex items-center justify-between rounded-[var(--radius-card-lg)] border border-border bg-card p-4 text-left shadow-card transition-shadow hover:shadow-card-hover"
              >
                <div>
                  <p className="text-sm font-semibold text-text">{draft.title}</p>
                  <p className="mt-0.5 text-xs text-muted">
                    {DOCUMENT_TYPE_LABELS[draft.document_type] ?? draft.document_type} · v{draft.version}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="rounded-full bg-accent-light px-2 py-0.5 text-[11px] font-semibold text-accent">
                    {draft.status}
                  </span>
                  {isOwner && (
                    <span
                      role="button"
                      tabIndex={0}
                      aria-label="Delete draft"
                      onClick={(e) => {
                        e.stopPropagation();
                        setDraftToDelete(draft);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.stopPropagation();
                          setDraftToDelete(draft);
                        }
                      }}
                      className="rounded-md p-1.5 text-muted hover:bg-red-light hover:text-red"
                    >
                      <Trash2 size={14} />
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>

        {showNewDraftModal && (
          <Modal onClose={() => (creatingDraft ? null : setShowNewDraftModal(false))}>
            <h3 className="mb-6 pr-6 text-lg font-bold text-text">New Draft</h3>
            <form onSubmit={handleCreateDraft} className="flex flex-col gap-4">
              <div>
                <label className="mb-1 block text-sm font-semibold text-text">Title</label>
                <input
                  type="text"
                  value={newDraftTitle}
                  onChange={(e) => setNewDraftTitle(e.target.value)}
                  placeholder="e.g. Literature Review Draft"
                  className="w-full rounded-lg border border-border px-3.5 py-2 text-sm"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-semibold text-text">Document type</label>
                <select
                  value={newDraftType}
                  onChange={(e) => setNewDraftType(e.target.value)}
                  className="w-full rounded-lg border border-border px-3 py-2 text-sm text-text"
                >
                  {DOCUMENT_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {DOCUMENT_TYPE_LABELS[type]}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-sm font-semibold text-text">
                  Content <span className="font-normal text-muted">(optional — can add later via Edit)</span>
                </label>
                <textarea
                  value={newDraftContent}
                  onChange={(e) => setNewDraftContent(e.target.value)}
                  rows={5}
                  placeholder="Start writing, or leave blank and fill it in afterward…"
                  className="w-full resize-y rounded-lg border border-border px-3.5 py-2 text-sm"
                />
              </div>
              {newDraftError && <ErrorBanner message={newDraftError} />}
              <div className="mt-2 flex gap-2.5">
                <button
                  type="button"
                  onClick={() => setShowNewDraftModal(false)}
                  disabled={creatingDraft}
                  className="btn-secondary flex-1 py-2.5"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!newDraftTitle.trim() || creatingDraft}
                  className="btn-primary flex-1 py-2.5"
                >
                  {creatingDraft ? "Creating..." : "Create Draft"}
                </button>
              </div>
            </form>
          </Modal>
        )}

        {draftToDelete && (
          <ConfirmDeleteModal
            title={`Delete "${draftToDelete.title}"?`}
            description="This permanently deletes this draft and its review comments. This cannot be undone."
            confirmLabel="Delete draft"
            deleting={deleting}
            error={deleteError}
            onConfirm={handleDeleteDraft}
            onClose={() => setDraftToDelete(null)}
          />
        )}
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

          <div className="mb-4 overflow-hidden rounded-[var(--radius-card-lg)] border border-border bg-card shadow-card">
            <div className="flex items-center justify-between border-b border-border px-5 py-3.5">
              <div className="flex items-center gap-2">
                <p className="text-sm font-bold text-text">Draft Content</p>
                <span className="rounded-full bg-border px-2 py-0.5 text-[11px] font-semibold text-muted">
                  v{selectedDraft.version}
                </span>
              </div>
              {editingContent ? (
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={cancelEditingContent}
                    disabled={savingContent}
                    className="flex items-center gap-1 text-xs font-semibold text-muted disabled:opacity-40"
                  >
                    <X size={12} /> Cancel
                  </button>
                  <button
                    type="button"
                    onClick={saveEditedContent}
                    disabled={savingContent}
                    className="btn-primary px-2.5 py-1 text-xs"
                  >
                    {savingContent ? "Saving..." : "Save"}
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={startEditingContent}
                  className="flex items-center gap-1 text-xs font-semibold text-accent"
                >
                  <Pencil size={12} /> Edit
                </button>
              )}
            </div>
            {editingContent ? (
              <textarea
                value={editedContent}
                onChange={(e) => setEditedContent(e.target.value)}
                rows={14}
                className="w-full resize-y border-none px-5 py-4 font-mono text-[13px] leading-relaxed text-text outline-none"
              />
            ) : (
              <div className="max-h-64 overflow-auto px-5 py-4">
                {selectedDraft.content ? (
                  splitIntoSections(selectedDraft.content).map((section, i) => (
                    <div key={i} className={i > 0 ? "mt-4" : undefined}>
                      {section.title && (
                        <p className="mb-1 text-xs font-bold text-text">{section.title}</p>
                      )}
                      <p className="whitespace-pre-wrap break-words text-[13.5px] leading-relaxed text-text">
                        {section.body}
                      </p>
                    </div>
                  ))
                ) : (
                  <p className="text-[13.5px] leading-relaxed text-text">This draft has no content yet.</p>
                )}
              </div>
            )}
          </div>

          <div className="mb-4 overflow-hidden rounded-[var(--radius-card-lg)] border border-border bg-card shadow-card">
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
            className="btn-primary w-full py-2.5"
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
          <form onSubmit={handleAddNote} className="mb-4 flex gap-2">
            <label htmlFor="manual-note" className="sr-only">
              Add a manual review note
            </label>
            <input
              id="manual-note"
              type="text"
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              placeholder="Add a note (not run through AI)…"
              className="flex-1 rounded-xl border border-border px-3.5 py-2 text-sm text-text outline-none transition-colors focus:border-accent"
            />
            <button
              type="submit"
              disabled={!noteText.trim() || addingNote}
              className="btn-secondary px-3 py-2 text-xs"
            >
              <Plus size={13} /> {addingNote ? "Adding..." : "Add note"}
            </button>
          </form>

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
              <p className="mb-3 text-xs text-muted">
                Accept/Dismiss only marks a suggestion as reviewed — it doesn't change the draft.
                To apply a suggestion, edit the draft content yourself using the{" "}
                <span className="font-semibold text-text">Edit</span> button.
              </p>
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
                    onDelete={handleDeleteComment}
                    canDelete={comment.user_id === user?.id || isOwner}
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
