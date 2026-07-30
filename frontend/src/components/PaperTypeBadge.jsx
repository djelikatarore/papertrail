export default function PaperTypeBadge({ detectedPaperType }) {
  if (!detectedPaperType) return null;

  return (
    <span className="whitespace-nowrap rounded-full bg-teal-light px-2 py-0.5 text-[11px] font-semibold tracking-wide text-teal">
      {detectedPaperType}
    </span>
  );
}
