import { useEffect, useState } from "react";

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

const SUMMARY_STAGE_LABELS = [
  "Extracting contribution",
  "Analyzing methodology",
  "Compiling key results",
  "Reviewing limitations",
];

// Generating the 4 summary blocks happens as a single Groq call on the
// backend (see summary_service.py::generate_summary) — there's no real
// per-block signal to report, so this is a simulated, time-based
// progression through the 4 stages rather than a true one. Caps at 92% so
// it never visually claims to be "done" while status is still PROCESSING;
// the tab content itself flips to the real result as soon as it's ready.
const ESTIMATED_SUMMARY_SECONDS = 40;

export function SummaryProgress({ startedAt }) {
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const elapsedSeconds = startedAt ? (now - new Date(startedAt).getTime()) / 1000 : 0;
  const fraction = Math.max(0, Math.min(0.92, elapsedSeconds / ESTIMATED_SUMMARY_SECONDS));
  const stageIndex = Math.min(3, Math.floor(fraction * 4));
  const percent = Math.round(fraction * 100);

  return (
    <div className="py-6">
      <div className="mb-2 flex items-center justify-between text-xs font-semibold text-muted">
        <span>{SUMMARY_STAGE_LABELS[stageIndex]}...</span>
        <span>{percent}%</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-app-bg">
        <div
          className="h-full rounded-full bg-accent transition-all duration-700 ease-out"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
