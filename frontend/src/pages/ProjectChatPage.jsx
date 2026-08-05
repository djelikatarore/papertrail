import { MessageSquare, Send, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import AppShell from "../components/AppShell";
import ErrorBanner from "../components/ErrorBanner";
import PaperCard from "../components/PaperCard";
import { listProjectPapers } from "../services/paperService";
import { askComparative, getProjectChatHistory } from "../services/projectService";

// Same shape as PaperDetailsPage's per-paper history: only role/content is
// ever persisted (chat_service.save_exchange), so citations/refused can't be
// recovered for past exchanges — only exchanges asked live in this session
// carry them.
function chatHistoryToExchanges(history) {
  const messages = history.flatMap((group) => group.messages);
  const exchanges = [];
  for (let i = 0; i < messages.length; i++) {
    if (messages[i].role !== "user") continue;
    const next = messages[i + 1];
    exchanges.push({
      question: messages[i].content,
      answer: next?.role === "assistant" ? next.content : "",
      citations: [],
      refused: false,
    });
  }
  return exchanges;
}

export default function ProjectChatPage() {
  const { workspaceId, projectId } = useParams();

  const [papers, setPapers] = useState([]);
  const [loadingPapers, setLoadingPapers] = useState(true);
  const [selectedIds, setSelectedIds] = useState(new Set());

  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState(null);
  const [exchanges, setExchanges] = useState([]);

  useEffect(() => {
    Promise.all([
      listProjectPapers(workspaceId, projectId, { limit: 100 }),
      getProjectChatHistory(workspaceId, projectId).catch(() => []),
    ])
      .then(([papersRes, history]) => {
        setPapers(papersRes.items);
        setExchanges(chatHistoryToExchanges(history));
      })
      .catch(() => setError("Could not load this project's papers."))
      .finally(() => setLoadingPapers(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceId, projectId]);

  const readyPapers = papers.filter((p) => p.status === "READY");

  function toggle(paperId) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(paperId) ? next.delete(paperId) : next.add(paperId);
      return next;
    });
  }

  async function handleAsk(event) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || selectedIds.size === 0 || asking) return;
    setAsking(true);
    setError(null);
    try {
      const res = await askComparative(workspaceId, projectId, {
        question: trimmed,
        paperIds: [...selectedIds],
      });
      setExchanges((prev) => [...prev, { question: trimmed, ...res }]);
      setQuestion("");
    } catch (err) {
      setError(err.response?.data?.detail ?? "Could not get an answer. Please try again.");
    } finally {
      setAsking(false);
    }
  }

  return (
    <AppShell
      workspaceId={workspaceId}
      title="AI Chat"
      subtitle="Ask a question across multiple papers at once"
    >
      <div className="grid grid-cols-1 gap-6 p-10 md:grid-cols-[260px_1fr]">
        <div className="h-fit rounded-[var(--radius-card-lg)] border border-border bg-card p-5 shadow-card md:sticky md:top-5">
          <p className="mb-3.5 text-sm font-bold text-text">Select papers</p>
          {loadingPapers ? (
            <p className="text-xs text-muted">Loading papers...</p>
          ) : readyPapers.length === 0 ? (
            <p className="text-xs text-muted">
              No papers are ready yet. Upload and wait for processing to finish first.
            </p>
          ) : (
            <div className="flex flex-col gap-2" role="group" aria-label="Select papers to include">
              {readyPapers.map((paper) => (
                <PaperCard
                  key={paper.id}
                  paper={paper}
                  selected={selectedIds.has(paper.id)}
                  onClick={() => toggle(paper.id)}
                />
              ))}
            </div>
          )}
          {selectedIds.size > 0 && (
            <p className="mt-2.5 text-center text-xs text-muted">
              {selectedIds.size} paper{selectedIds.size > 1 ? "s" : ""} selected
            </p>
          )}
        </div>

        <div className="rounded-[var(--radius-card-lg)] border border-border bg-card p-6 shadow-card">
          {exchanges.length === 0 ? (
            <div className="py-16 text-center text-muted">
              <MessageSquare size={36} strokeWidth={1} className="mx-auto mb-3 text-border" />
              <p className="mb-1 text-sm font-semibold text-text">No questions yet</p>
              <p className="text-[13px]">Select one or more papers and ask a comparative question</p>
            </div>
          ) : (
            <div className="mb-5 flex flex-col gap-4">
              {exchanges.map((ex, i) => (
                <div key={i} className="flex flex-col gap-2.5">
                  <div className="flex justify-end">
                    <div className="max-w-[80%] rounded-2xl rounded-tr-md bg-accent px-4 py-2.5 text-sm text-white">
                      {ex.question}
                    </div>
                  </div>
                  <div className="flex items-start gap-2.5">
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-accent">
                      <Sparkles size={13} className="text-white" strokeWidth={1.5} />
                    </div>
                    <div className="flex max-w-[80%] flex-col gap-1.5">
                      <div
                        className={`rounded-2xl rounded-tl-md px-4 py-2.5 text-sm leading-relaxed ${
                          ex.refused ? "border border-border text-muted italic" : "bg-app-bg text-text"
                        }`}
                      >
                        {ex.answer}
                      </div>
                      {!ex.refused && ex.citations?.length > 0 && (
                        <div className="flex flex-col gap-1 px-1">
                          {ex.citations
                            .filter((c) => c.cited_section)
                            .map((c) => (
                              <p key={c.paper_id} className="text-xs text-muted">
                                {c.title}: {c.cited_section}
                              </p>
                            ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {error && (
            <div className="mb-4">
              <ErrorBanner message={error} />
            </div>
          )}

          <form onSubmit={handleAsk} className="flex gap-2">
            <label htmlFor="comparative-question" className="sr-only">
              Ask a question across the selected papers
            </label>
            <input
              id="comparative-question"
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={
                selectedIds.size === 0
                  ? "Select at least one paper first…"
                  : "Ask a question across the selected papers…"
              }
              className="flex-1 rounded-xl border border-border px-3.5 py-2.5 text-sm text-text outline-none transition-colors focus:border-accent"
            />
            <button
              type="submit"
              disabled={!question.trim() || selectedIds.size === 0 || asking}
              className="btn-primary shrink-0 px-4 py-2.5"
            >
              <Send size={13} /> {asking ? "Asking..." : "Ask"}
            </button>
          </form>
        </div>
      </div>
    </AppShell>
  );
}
