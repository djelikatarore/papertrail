import ErrorBanner from "./ErrorBanner";
import Modal from "./Modal";

// Shown once per paper (see PaperDetailsPage's use of localStorage to track
// this) the first time the user lands on a paper whose AI classification
// flagged it as not looking like an academic paper. The warning banner on
// Paper Details stays up regardless of what's chosen here — this is just the
// one-time "make sure you noticed" nudge on top of it.
export default function NonAcademicWarningModal({ onKeep, onDelete, deleting, error }) {
  return (
    <Modal onClose={deleting ? () => {} : onKeep} maxWidth="max-w-sm">
      <h3 className="mb-3 pr-6 text-lg font-bold text-text">Heads up</h3>
      <p className="mb-4 text-sm font-semibold text-red">
        This document doesn't look like an academic paper.
      </p>
      <p className="mb-5 text-sm text-muted">
        The AI-generated summary and keywords may not be very useful for it. You can keep it in
        this project anyway, or delete it and upload a different file instead.
      </p>
      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}
      <div className="flex gap-2.5">
        <button type="button" onClick={onKeep} disabled={deleting} className="btn-secondary flex-1 py-2.5">
          Keep it anyway
        </button>
        <button
          type="button"
          onClick={onDelete}
          disabled={deleting}
          className="flex-1 rounded-xl bg-red py-2.5 text-sm font-semibold text-white transition-colors hover:bg-red/85 disabled:opacity-40"
        >
          {deleting ? "Deleting..." : "Delete and upload another file"}
        </button>
      </div>
    </Modal>
  );
}
