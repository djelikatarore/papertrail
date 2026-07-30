// Figma's PaperDetailsScreen shows a year/citation-based SVG citation graph —
// our backend has no year, author, or citation-count fields at all, so that
// specific visualization can't be honestly reproduced. This shows the same
// underlying relationship (how closely this paper relates to others in the
// project) using the real data we do have: embedding similarity.
export default function SimilarityPanel({ similarPapers }) {
  if (!similarPapers || similarPapers.length === 0) {
    return <p className="text-sm text-muted">No other papers in this project yet to compare against.</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      {similarPapers.map((sp) => {
        const pct = Math.round(sp.similarity * 100);
        return (
          <div key={sp.paper_id}>
            <div className="mb-1 flex items-center justify-between">
              <p className="text-sm font-medium text-text">{sp.title ?? sp.filename}</p>
              <span className="text-xs font-semibold text-muted">{pct}%</span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-border">
              <div className="h-full rounded-full bg-accent" style={{ width: `${pct}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
