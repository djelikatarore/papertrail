import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import AppShell from "../components/AppShell";
import CitationGraphBarChart from "../components/CitationGraphBarChart";
import ErrorBanner from "../components/ErrorBanner";
import { getCitationGraph } from "../services/projectService";

export default function CitationGraphPage() {
  const { workspaceId, projectId } = useParams();
  const navigate = useNavigate();

  const [nodes, setNodes] = useState([]);
  const [links, setLinks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getCitationGraph(workspaceId, projectId)
      .then((graph) => {
        setNodes(graph.nodes.map((n) => ({ id: n.paper_id, title: n.title })));
        setLinks(graph.links);
      })
      .catch(() => setError("Could not load the citation graph. Please try again."))
      .finally(() => setLoading(false));
  }, [workspaceId, projectId]);

  return (
    <AppShell
      workspaceId={workspaceId}
      title="Citation Graph"
      subtitle="How papers in this project relate to each other"
    >
      <div className="p-10">
        {error && (
          <div className="mb-6">
            <ErrorBanner message={error} />
          </div>
        )}

        {loading ? (
          <p className="text-sm text-muted">Loading...</p>
        ) : (
          <div className="rounded-[var(--radius-card-lg)] border border-border bg-card p-6 shadow-card">
            <CitationGraphBarChart
              nodes={nodes}
              links={links}
              onNodeClick={(paperId) =>
                navigate(`/workspaces/${workspaceId}/projects/${projectId}/papers/${paperId}`)
              }
            />
          </div>
        )}
      </div>
    </AppShell>
  );
}
