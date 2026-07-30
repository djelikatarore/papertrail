import { useAuth } from "../context/AuthContext";

export default function DashboardPage() {
  const { user, logout } = useAuth();

  return (
    <div className="flex min-h-screen bg-app-bg">
      <aside className="w-64 shrink-0 bg-sidebar p-6 text-white">
        <div className="text-lg font-semibold">PaperTrail</div>
        <nav className="mt-8 flex flex-col gap-2 text-sm text-white/70">
          <span>Dashboard</span>
          <span>Workspaces</span>
        </nav>
      </aside>

      <main className="flex-1 p-8">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-xl font-semibold text-gray-900">Dashboard</h1>
          <button
            onClick={logout}
            className="rounded-card bg-accent px-4 py-2 text-sm font-medium text-white"
          >
            Log out
          </button>
        </div>

        <div className="rounded-card bg-white p-6 shadow-card">
          <p className="text-sm text-gray-500">
            {user ? `Signed in as ${user.full_name}` : "Design system test card."}
          </p>
        </div>
      </main>
    </div>
  );
}
