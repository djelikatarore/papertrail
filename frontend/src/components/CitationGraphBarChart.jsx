const WIDTH = 760;
const HEIGHT = 420;
const PADDING_X = 40;
const PADDING_TOP = 30;
const PADDING_BOTTOM = 70;
const MIN_BAR_HEIGHT = 4;
const BAR_WIDTH_RATIO = 0.6;

function truncate(text, max) {
  if (!text) return "";
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

// A paper's bar height is its real academic citation count, looked up from
// CrossRef by title during background processing (see crossref_service.py) —
// not content similarity between the user's own papers. citationCount is
// null when no confident CrossRef match was found (or the lookup hasn't run
// yet), which is shown distinctly (gray bar, "Not found" label) rather than
// being treated as 0 citations — those are two very different things.
export default function CitationGraphBarChart({ nodes, onNodeClick }) {
  if (nodes.length === 0) {
    return (
      <div className="py-16 text-center text-muted">
        <p className="text-sm font-semibold text-text">Not enough data yet</p>
        <p className="mt-1 text-[13px]">Papers need to finish processing before citation counts can be graphed.</p>
      </div>
    );
  }

  const knownCounts = nodes.map((n) => n.citationCount).filter((c) => c != null);
  const maxCount = Math.max(...knownCounts, 1);
  const chartHeight = HEIGHT - PADDING_TOP - PADDING_BOTTOM;
  const slotWidth = (WIDTH - PADDING_X * 2) / nodes.length;
  const barWidth = slotWidth * BAR_WIDTH_RATIO;
  const titleMaxChars = Math.max(6, Math.floor(slotWidth / 6.5));

  return (
    <div id="citation-graph-bar-chart">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full" style={{ height: "auto" }}>
        {nodes.map((node, i) => {
          const known = node.citationCount != null;
          const barHeight = known
            ? Math.max((node.citationCount / maxCount) * chartHeight, MIN_BAR_HEIGHT)
            : MIN_BAR_HEIGHT;
          const x = PADDING_X + i * slotWidth + (slotWidth - barWidth) / 2;
          const y = HEIGHT - PADDING_BOTTOM - barHeight;

          return (
            <g key={node.id} onClick={() => onNodeClick(node.id)} className="group cursor-pointer">
              <title>{node.title}</title>
              <text x={x + barWidth / 2} y={y - 8} textAnchor="middle" className="fill-muted text-[10px]">
                {known ? node.citationCount.toLocaleString() : "Not found"}
              </text>
              <rect
                x={x}
                y={y}
                width={barWidth}
                height={barHeight}
                rx={4}
                className={
                  known
                    ? "fill-accent transition-colors group-hover:fill-accent-dark"
                    : "fill-border transition-colors group-hover:fill-muted"
                }
              />
              <text
                x={x + barWidth / 2}
                y={HEIGHT - PADDING_BOTTOM + 18}
                textAnchor="middle"
                className="fill-text text-[11px] font-semibold"
              >
                {truncate(node.title, titleMaxChars)}
              </text>
            </g>
          );
        })}
        <line
          x1={PADDING_X}
          y1={HEIGHT - PADDING_BOTTOM}
          x2={WIDTH - PADDING_X}
          y2={HEIGHT - PADDING_BOTTOM}
          className="stroke-border"
          strokeWidth={1}
        />
      </svg>
      <p className="mt-2 text-center text-xs text-muted">Citation counts from Semantic Scholar (CrossRef as fallback).</p>
      <p className="mt-0.5 text-center text-[11px] text-muted/70">
        A paper may show "Not found" if neither source has a confident match, or CrossRef's fallback count
        may undercount preprints and conference papers common in CS/ML research.
      </p>
    </div>
  );
}
