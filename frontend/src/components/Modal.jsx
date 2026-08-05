import { X } from "lucide-react";

// Shared overlay shell for every modal in the app: backdrop, centering,
// click-outside-to-close, and a close X consistently pinned to the card's
// top-right corner. Callers render their own header/body/footer as children
// — this only owns the parts that must behave identically everywhere.
export default function Modal({ onClose, maxWidth = "max-w-md", children }) {
  return (
    <div
      className="fixed inset-0 z-[300] flex items-center justify-center bg-text/40 animate-fade-in"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
        className={`relative w-full ${maxWidth} animate-modal-in rounded-[var(--radius-card-lg)] bg-card p-8 shadow-modal`}
      >
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="absolute right-5 top-5 text-muted hover:text-text"
        >
          <X size={18} />
        </button>
        {children}
      </div>
    </div>
  );
}
