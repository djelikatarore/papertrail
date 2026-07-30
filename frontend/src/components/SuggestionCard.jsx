import { Check, X } from "lucide-react";

const STATUS_STYLES = {
  OPEN: { bg: "bg-amber-light", text: "text-amber", label: "Pending" },
  ACCEPTED: { bg: "bg-green-light", text: "text-green", label: "Accepted" },
  DISMISSED: { bg: "bg-border", text: "text-muted", label: "Dismissed" },
};

// ReviewComment currently only has `content` + `status` — no structured
// original/suggested/reason breakdown. This card renders that flat shape by
// default, but accepts optional `original`/`suggested`/`reason` props so a
// richer diff view can be dropped in later without changing the list/page
// that renders these cards.
export default function SuggestionCard({ comment, onAccept, onDismiss, original, suggested, reason }) {
  const style = STATUS_STYLES[comment.status] ?? STATUS_STYLES.OPEN;
  const isPending = comment.status === "OPEN";
  const hasDiff = original != null && suggested != null;

  return (
    <div
      className={`rounded-card border border-border bg-card transition-opacity ${
        comment.status === "DISMISSED" ? "opacity-50" : "opacity-100"
      }`}
    >
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <span className={`rounded-md px-2 py-0.5 text-[11px] font-semibold ${style.bg} ${style.text}`}>
          {style.label}
        </span>
        {isPending ? (
          <div className="flex gap-1.5">
            <button
              type="button"
              onClick={() => onAccept(comment)}
              className="flex items-center gap-1 rounded-md bg-green-light px-2.5 py-1 text-xs font-semibold text-green"
            >
              <Check size={11} /> Accept
            </button>
            <button
              type="button"
              onClick={() => onDismiss(comment)}
              className="flex items-center gap-1 rounded-md bg-border px-2.5 py-1 text-xs font-semibold text-muted"
            >
              <X size={11} /> Dismiss
            </button>
          </div>
        ) : null}
      </div>
      <div className="px-4 py-3.5">
        {hasDiff ? (
          <>
            <div className="mb-2.5">
              <p className="mb-1 text-[10px] font-bold uppercase tracking-wide text-muted">Original</p>
              <p className="rounded-md bg-red-light px-2.5 py-2 text-[12.5px] leading-relaxed text-red">
                {original}
              </p>
            </div>
            <div className="mb-2.5">
              <p className="mb-1 text-[10px] font-bold uppercase tracking-wide text-muted">Suggested</p>
              <p className="rounded-md bg-green-light px-2.5 py-2 text-[12.5px] leading-relaxed text-green">
                {suggested}
              </p>
            </div>
            {reason && <p className="text-[11.5px] italic leading-relaxed text-muted">{reason}</p>}
          </>
        ) : (
          <p className="text-[13px] leading-relaxed text-text">{comment.content}</p>
        )}
      </div>
    </div>
  );
}
