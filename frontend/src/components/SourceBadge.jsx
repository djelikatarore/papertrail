const SOURCE_STYLES = {
  arxiv: { bg: "bg-accent-light", text: "text-accent", label: "arXiv" },
  core: { bg: "bg-teal-light", text: "text-teal", label: "CORE" },
  pubmed: { bg: "bg-green-light", text: "text-green", label: "PubMed" },
};

export default function SourceBadge({ source }) {
  const style = SOURCE_STYLES[source] ?? { bg: "bg-border", text: "text-muted", label: source };

  return (
    <span
      className={`whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-semibold tracking-wide ${style.bg} ${style.text}`}
    >
      {style.label}
    </span>
  );
}
