import { useMemo } from "react";

const WIDTH = 760;
const HEIGHT = 480;
const PADDING = 50;
const MIN_RADIUS = 14;
const MAX_RADIUS = 34;
const ITERATIONS = 300;
const REPULSION = 12000;
const SPRING = 0.02;
const CENTER_PULL = 0.01;
const DAMPING = 0.85;

// Dependency-free force-directed layout — a project's papers are typically a
// few dozen at most, so a plain O(n^2) repulsion pass per iteration is cheap
// enough that pulling in d3-force (or any layout library) isn't justified.
// Runs to a static, converged layout up front rather than animating frame by
// frame, since nothing here needs to move once positioned (no drag support).
function computeLayout(nodes, links) {
  const positions = {};
  const velocities = {};
  const n = nodes.length;
  if (n === 0) return positions;

  const ringRadius = Math.min(WIDTH, HEIGHT) / 2.8;
  nodes.forEach((node, i) => {
    const angle = (i / n) * 2 * Math.PI;
    positions[node.id] = {
      x: WIDTH / 2 + ringRadius * Math.cos(angle),
      y: HEIGHT / 2 + ringRadius * Math.sin(angle),
    };
    velocities[node.id] = { x: 0, y: 0 };
  });

  for (let iter = 0; iter < ITERATIONS; iter++) {
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        const a = positions[nodes[i].id];
        const b = positions[nodes[j].id];
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const dist = Math.hypot(dx, dy) || 0.01;
        const force = REPULSION / (dist * dist);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        velocities[nodes[i].id].x += fx;
        velocities[nodes[i].id].y += fy;
        velocities[nodes[j].id].x -= fx;
        velocities[nodes[j].id].y -= fy;
      }
    }

    for (const link of links) {
      const a = positions[link.source];
      const b = positions[link.target];
      if (!a || !b) continue;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.hypot(dx, dy) || 0.01;
      // Stronger similarity pulls papers closer together.
      const idealLength = 260 - 180 * link.weight;
      const force = SPRING * (dist - idealLength);
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      velocities[link.source].x += fx;
      velocities[link.source].y += fy;
      velocities[link.target].x -= fx;
      velocities[link.target].y -= fy;
    }

    for (const node of nodes) {
      const p = positions[node.id];
      velocities[node.id].x += (WIDTH / 2 - p.x) * CENTER_PULL;
      velocities[node.id].y += (HEIGHT / 2 - p.y) * CENTER_PULL;
    }

    for (const node of nodes) {
      const v = velocities[node.id];
      const p = positions[node.id];
      v.x *= DAMPING;
      v.y *= DAMPING;
      p.x += v.x;
      p.y += v.y;
    }
  }

  for (const node of nodes) {
    const p = positions[node.id];
    p.x = Math.min(WIDTH - PADDING, Math.max(PADDING, p.x));
    p.y = Math.min(HEIGHT - PADDING, Math.max(PADDING, p.y));
  }

  return positions;
}

function truncate(text, max) {
  if (!text) return "";
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

export default function CitationGraphCanvas({ nodes, links, onNodeClick }) {
  const positions = useMemo(() => computeLayout(nodes, links), [nodes, links]);

  const weightedDegree = useMemo(() => {
    const deg = {};
    nodes.forEach((n) => { deg[n.id] = 0; });
    links.forEach((l) => {
      deg[l.source] = (deg[l.source] ?? 0) + l.weight;
      deg[l.target] = (deg[l.target] ?? 0) + l.weight;
    });
    return deg;
  }, [nodes, links]);

  const degreeValues = Object.values(weightedDegree);
  const maxDegree = degreeValues.length ? Math.max(...degreeValues) : 0;
  const minDegree = degreeValues.length ? Math.min(...degreeValues) : 0;

  function radiusFor(id) {
    if (maxDegree === minDegree) return (MIN_RADIUS + MAX_RADIUS) / 2;
    const t = (weightedDegree[id] - minDegree) / (maxDegree - minDegree);
    return MIN_RADIUS + t * (MAX_RADIUS - MIN_RADIUS);
  }

  const weights = links.map((l) => l.weight);
  const maxWeight = weights.length ? Math.max(...weights) : 0;
  const minWeight = weights.length ? Math.min(...weights) : 0;

  function styleForWeight(w) {
    const t = maxWeight === minWeight ? 1 : (w - minWeight) / (maxWeight - minWeight);
    return { strokeWidth: 1 + t * 4, opacity: 0.25 + t * 0.6 };
  }

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

  return (
    <div id="citation-graph-canvas">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full" style={{ height: "auto" }}>
        {links.map((link, i) => {
          const a = positions[link.source];
          const b = positions[link.target];
          if (!a || !b) return null;
          const { strokeWidth, opacity } = styleForWeight(link.weight);
          return (
            <line
              key={i}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke="var(--color-accent)"
              strokeWidth={strokeWidth}
              opacity={opacity}
            />
          );
        })}

        {nodes.map((node) => {
          const pos = positions[node.id];
          if (!pos) return null;
          const r = radiusFor(node.id);
          return (
            <g
              key={node.id}
              transform={`translate(${pos.x}, ${pos.y})`}
              onClick={() => onNodeClick(node.id)}
              className="cursor-pointer"
            >
              <circle r={r} fill="var(--color-accent-light)" stroke="var(--color-accent)" strokeWidth={1.5} />
              <text
                y={r + 14}
                textAnchor="middle"
                className="fill-text text-[11px] font-semibold"
              >
                {truncate(node.title, 24)}
              </text>
              <text
                y={r + 27}
                textAnchor="middle"
                className="fill-muted text-[10px]"
              >
                {node.detectedPaperType ? truncate(node.detectedPaperType, 26) : "Unknown type"}
              </text>
            </g>
          );
        })}
      </svg>
      <p className="mt-2 text-center text-xs text-muted">Graph based on paper similarity.</p>
    </div>
  );
}
