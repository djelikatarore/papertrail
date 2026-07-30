const REVIEW_TYPE_STYLES = {
  SYSTEMATIC: { bg: "bg-accent-light", text: "text-accent", label: "Systematic" },
  SCOPING: { bg: "bg-teal-light", text: "text-teal", label: "Scoping" },
  CRITICAL: { bg: "bg-red-light", text: "text-red", label: "Critical" },
  NARRATIVE: { bg: "bg-amber-light", text: "text-amber", label: "Narrative" },
  RAPID: { bg: "bg-green-light", text: "text-green", label: "Rapid" },
};

export default function ReviewTypeBadge({ reviewType }) {
  const style = REVIEW_TYPE_STYLES[reviewType];
  if (!style) return null;

  return (
    <span
      className={`whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-semibold tracking-wide ${style.bg} ${style.text}`}
    >
      {style.label}
    </span>
  );
}
