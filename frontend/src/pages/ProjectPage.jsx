import { useParams } from "react-router-dom";

export default function ProjectPage() {
  const { workspaceId, projectId } = useParams();

  return (
    <div className="min-h-screen bg-app-bg p-8">
      <div className="rounded-card bg-white p-6 shadow-card">
        <h1 className="text-xl font-semibold text-gray-900">
          Project {projectId} (workspace {workspaceId})
        </h1>
        <p className="mt-2 text-sm text-gray-500">Paper library goes here.</p>
      </div>
    </div>
  );
}
