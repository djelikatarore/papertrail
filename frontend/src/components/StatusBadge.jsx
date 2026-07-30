const STATUS_STYLES = {
  PROCESSING: { bg: "bg-amber-light", text: "text-amber", label: "Processing" },
  READY: { bg: "bg-green-light", text: "text-green", label: "Ready" },
  ERROR: { bg: "bg-red-light", text: "text-red", label: "Error" },
};

export function StatusPill({ status }) {
  const style = STATUS_STYLES[status];
  if (!style) return null;

  return (
    <span
      className={`whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-semibold tracking-wide ${style.bg} ${style.text}`}
    >
      {style.label}
    </span>
  );
}

// Figure-description progress only makes sense while a paper is still
// PROCESSING and actually has figures to describe (visual_elements_total is
// only set once figure extraction has started — see backend/app/routers/
// paper_router.py::_process_paper_background). Rendered separately from
// StatusPill so callers that already show the pill in a badge row don't get
// it twice.
export default function FigureProgress({ paper }) {
  const showFigureProgress =
    paper.status === "PROCESSING" &&
    paper.visual_elements_total != null &&
    paper.visual_elements_total > 0;

  if (!showFigureProgress) return null;

  return (
    <div className="mt-1.5">
      <p className="text-xs text-muted">
        Describing figures: {paper.visual_elements_processed ?? 0}/{paper.visual_elements_total}
      </p>
      <p className="text-xs text-muted/70">This may take longer for papers with many figures</p>
    </div>
  );
}
