import { Check } from "lucide-react";
import PaperTypeBadge from "./PaperTypeBadge";
import ReviewTypeBadge from "./ReviewTypeBadge";
import FigureProgress, { StatusPill } from "./StatusBadge";

// `selected` is optional and only meaningful when a caller (e.g. Draft
// Generation's multi-select paper picker) passes it — plain usage (Library
// list, onClick navigates to Paper Details) is unaffected.
export default function PaperCard({ paper, onClick, selected }) {
  // Real title is only known once processing has extracted it — filename is
  // never shown to the user, but it's the only thing we have while PROCESSING.
  const displayTitle = paper.title ?? paper.filename;
  const isSelectable = selected !== undefined;

  return (
    <div
      onClick={onClick}
      role={isSelectable ? "checkbox" : undefined}
      aria-checked={isSelectable ? selected : undefined}
      tabIndex={isSelectable ? 0 : undefined}
      onKeyDown={
        isSelectable
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onClick?.();
              }
            }
          : undefined
      }
      className={`cursor-pointer rounded-card border bg-card p-5 shadow-card transition-shadow hover:shadow-card-hover ${
        isSelectable && selected ? "border-accent ring-1 ring-accent" : "border-border"
      }`}
    >
      <div className="mb-2.5 flex items-start justify-between gap-3">
        {isSelectable && (
          <span
            className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded ${
              selected ? "bg-accent text-white" : "border border-border"
            }`}
          >
            {selected && <Check size={11} strokeWidth={3} />}
          </span>
        )}
        <p className="flex-1 text-sm font-semibold leading-snug text-text">{displayTitle}</p>
        <div className="flex shrink-0 flex-wrap items-center gap-1.5">
          <StatusPill status={paper.status} />
          <ReviewTypeBadge reviewType={paper.review_type} />
          <PaperTypeBadge detectedPaperType={paper.detected_paper_type} />
        </div>
      </div>
      {paper.status === "ERROR" && paper.error_message && (
        <p className="text-xs text-red">{paper.error_message}</p>
      )}
      <FigureProgress paper={paper} />
    </div>
  );
}
