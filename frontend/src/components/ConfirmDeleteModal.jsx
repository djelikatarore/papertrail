import ErrorBanner from "./ErrorBanner";
import Modal from "./Modal";

// Shared destructive-confirmation shell — same structure previously
// duplicated across ProjectPage (delete project) and DraftReviewPage
// (delete draft): heading, warning copy, error banner, Cancel/destructive
// action pair. Callers own only their own copy and delete handler.
export default function ConfirmDeleteModal({
  title,
  description,
  confirmLabel,
  deletingLabel = "Deleting...",
  deleting,
  error,
  onConfirm,
  onClose,
}) {
  return (
    <Modal onClose={() => (deleting ? null : onClose())} maxWidth="max-w-sm">
      <h3 className="mb-2 pr-6 text-lg font-bold text-text">{title}</h3>
      <p className="mb-5 text-sm text-muted">{description}</p>
      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}
      <div className="flex gap-2.5">
        <button type="button" onClick={onClose} disabled={deleting} className="btn-secondary flex-1 py-2.5">
          Cancel
        </button>
        <button
          type="button"
          onClick={onConfirm}
          disabled={deleting}
          className="flex-1 rounded-xl bg-red py-2.5 text-sm font-semibold text-white transition-colors hover:bg-red/85 disabled:opacity-40"
        >
          {deleting ? deletingLabel : confirmLabel}
        </button>
      </div>
    </Modal>
  );
}
