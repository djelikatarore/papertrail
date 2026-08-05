import { ExternalLink, FileDown, Search as SearchIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import AppShell from "../components/AppShell";
import ErrorBanner from "../components/ErrorBanner";
import SourceBadge from "../components/SourceBadge";
import { getProject, suggestPapers } from "../services/projectService";

export default function SearchPage() {
  const { workspaceId, projectId } = useParams();

  const [project, setProject] = useState(null);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [category, setCategory] = useState("");
  const [author, setAuthor] = useState("");
  const [results, setResults] = useState(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    getProject(workspaceId, projectId).then(setProject).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceId, projectId]);

  async function handleSearch(event) {
    event.preventDefault();
    setSearching(true);
    setError(null);
    try {
      const data = await suggestPapers(workspaceId, projectId, { dateFrom, dateTo, category, author });
      setResults(data);
    } catch (err) {
      setError(err.response?.data?.detail ?? "Search failed. Please try again.");
    } finally {
      setSearching(false);
    }
  }

  return (
    <AppShell
      workspaceId={workspaceId}
      title="Suggested Papers"
      subtitle={project ? `Based on "${project.topic}" — sources: arXiv, CORE, PubMed` : undefined}
    >
      <div className="p-10">
        <form
          onSubmit={handleSearch}
          className="mb-6 grid grid-cols-4 gap-3 rounded-[var(--radius-card-lg)] border border-border bg-card p-5 shadow-card"
        >
          <div>
            <label className="mb-1 block text-xs font-semibold text-muted">From year</label>
            <input
              type="number"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              placeholder="e.g. 2018"
              className="w-full rounded-lg border border-border px-3 py-1.5 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold text-muted">To year</label>
            <input
              type="number"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              placeholder="e.g. 2024"
              className="w-full rounded-lg border border-border px-3 py-1.5 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold text-muted">Category (arXiv)</label>
            <input
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="e.g. cs.CL"
              className="w-full rounded-lg border border-border px-3 py-1.5 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold text-muted">Author</label>
            <input
              type="text"
              value={author}
              onChange={(e) => setAuthor(e.target.value)}
              placeholder="e.g. Vaswani"
              className="w-full rounded-lg border border-border px-3 py-1.5 text-sm"
            />
          </div>
          <button type="submit" disabled={searching} className="btn-primary col-span-4 py-2">
            <SearchIcon size={14} /> {searching ? "Searching..." : "Find suggested papers"}
          </button>
        </form>

        {error && (
          <div className="mb-6">
            <ErrorBanner message={error} />
          </div>
        )}

        {results && results.length === 0 && (
          <p className="text-sm text-muted">No suggestions found for this topic and filters.</p>
        )}

        {results && results.length > 0 && (
          <div className="flex flex-col gap-3">
            {results.map((paper, i) => (
              <div key={i} className="rounded-[var(--radius-card-lg)] border border-border bg-card p-5 shadow-card transition-shadow hover:shadow-card-hover">
                <div className="mb-1.5 flex items-start justify-between gap-3">
                  <p className="text-sm font-semibold leading-snug text-text">{paper.title}</p>
                  <SourceBadge source={paper.source} />
                </div>
                <p className="mb-2 text-xs text-muted">
                  {paper.authors.join(", ")} {paper.published_date ? `· ${paper.published_date}` : ""}
                </p>
                <p className="mb-3 text-sm leading-relaxed text-text">
                  {paper.abstract.length > 280 ? `${paper.abstract.slice(0, 280)}...` : paper.abstract}
                </p>
                {paper.pdf_link && (
                  <a
                    href={paper.pdf_link}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 text-sm font-semibold text-accent"
                  >
                    {paper.access_type === "direct_pdf" ? (
                      <>
                        <FileDown size={14} /> Direct PDF
                      </>
                    ) : (
                      <>
                        <ExternalLink size={14} /> View on publisher site
                      </>
                    )}
                  </a>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
