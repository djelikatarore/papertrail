import SimilarityRing from "./SimilarityRing";

// Shows how this paper relates to others in the project using the real data
// we have: embedding similarity. The dedicated Citation Graph page covers the
// visual "network of relationships" concept — this is the compact list form.
export default function SimilarityPanel({ similarPapers }) {
  if (!similarPapers || similarPapers.length === 0) {
    return <p className="text-sm text-muted">No other papers in this project yet to compare against.</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      {similarPapers.map((sp) => {
        const pct = Math.round(sp.similarity * 100);
        return (
          <div key={sp.paper_id} className="flex items-center gap-3.5">
            <SimilarityRing percentage={pct} size={36} />
            <p className="min-w-0 flex-1 truncate text-sm font-medium text-text">
              {sp.title ?? sp.filename}
            </p>
          </div>
        );
      })}
    </div>
  );
}
