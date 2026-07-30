import { useParams } from "react-router-dom";

export default function WorkspacePage() {
  const { workspaceId } = useParams();

  return (
    <div className="min-h-screen bg-app-bg p-8">
      <div className="rounded-card bg-white p-6 shadow-card">
        <h1 className="text-xl font-semibold text-gray-900">Workspace {workspaceId}</h1>
        <p className="mt-2 text-sm text-gray-500">Project list goes here.</p>
      </div>
    </div>
  );
}
