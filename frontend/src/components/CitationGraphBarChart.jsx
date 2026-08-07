import { useMemo } from "react";

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

// A paper's bar height is its total similarity — the sum of the similarity
// weight of every link touching it (same underlying data the previous
// node/link graph used for node size), not just its similarity to one other
// paper. Every paper in the project gets a bar, even one with no links above
// the similarity threshold (MIN_BAR_HEIGHT keeps it visible rather than
// invisible at height 0, so "one paper = one bar" always holds).
export default function CitationGraphBarChart({ nodes, links, onNodeClick }) {
  const totalSimilarity = useMemo(() => {
    const totals = {};
    nodes.forEach((n) => { totals[n.id] = 0; });
    links.forEach((l) => {
      totals[l.source] = (totals[l.source] ?? 0) + l.weight;
      totals[l.target] = (totals[l.target] ?? 0) + l.weight;
    });
    return totals;
  }, [nodes, links]);

  if (nodes.length === 0) {
    return (
      <div className="py-16 text-center text-muted">
        <p className="text-sm font-semibold text-text">Not enough data yet</p>
        <p className="mt-1 text-[13px]">
          Papers need to finish processing before similarity relationships can be graphed.
        </p>
      </div>
    );
  }

  const maxTotal = Math.max(...nodes.map((n) => totalSimilarity[n.id] ?? 0), 0);
  const chartHeight = HEIGHT - PADDING_TOP - PADDING_BOTTOM;
  const slotWidth = (WIDTH - PADDING_X * 2) / nodes.length;
  const barWidth = slotWidth * BAR_WIDTH_RATIO;
  const titleMaxChars = Math.max(6, Math.floor(slotWidth / 6.5));

  return (
    <div id="citation-graph-bar-chart">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full" style={{ height: "auto" }}>
        {nodes.map((node, i) => {
          const value = totalSimilarity[node.id] ?? 0;
          const barHeight = maxTotal > 0 ? Math.max((value / maxTotal) * chartHeight, MIN_BAR_HEIGHT) : MIN_BAR_HEIGHT;
          const x = PADDING_X + i * slotWidth + (slotWidth - barWidth) / 2;
          const y = HEIGHT - PADDING_BOTTOM - barHeight;

          return (
            <g
              key={node.id}
              onClick={() => onNodeClick(node.id)}
              className="group cursor-pointer"
            >
              <title>{node.title}</title>
              <text
                x={x + barWidth / 2}
                y={y - 8}
                textAnchor="middle"
                className="fill-muted text-[10px]"
              >
                {value.toFixed(2)}
              </text>
              <rect
                x={x}
                y={y}
                width={barWidth}
                height={barHeight}
                rx={4}
                className="fill-accent transition-colors group-hover:fill-accent-dark"
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
      <p className="mt-2 text-center text-xs text-muted">Graph based on paper similarity.</p>
    </div>
  );
}
