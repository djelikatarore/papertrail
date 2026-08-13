import {
  FileText,
  FolderOpen,
  LayoutDashboard,
  MessageSquare,
  PenTool,
  Search,
  Settings,
  Sparkles,
  Upload,
} from "lucide-react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

// Upload Paper / Similar Papers / Draft Generation / Draft Review are real,
// working screens — but each needs a project (and Similar Papers also a
// paper) selected
// first, and the sidebar has no picker of its own. So rather than a
// permanent "coming soon" placeholder, these items activate/deactivate based
// on whatever project/paper context the current route already has (read via
// useParams() from wherever the route tree currently is), exactly like a
// real app would grey out a nav item that needs a selection first — not
// mislabel a working feature as unbuilt.
const SECTIONS = (workspaceId, projectId, paperId) => [
  {
    label: "Workspace",
    items: [
      { label: "Dashboard", icon: LayoutDashboard, to: "/dashboard" },
      { label: "Workspace", icon: FolderOpen, to: "/workspaces" },
    ],
  },
  {
    label: "Paper Tools",
    items: [
      {
        label: "Upload Paper",
        icon: Upload,
        to: projectId ? `/workspaces/${workspaceId}/projects/${projectId}?upload=1` : undefined,
        inert: !projectId,
      },
      {
        label: "AI Chat",
        icon: MessageSquare,
        to: projectId ? `/workspaces/${workspaceId}/projects/${projectId}/chat` : undefined,
        inert: !projectId,
      },
      {
        label: "Similar Papers",
        icon: Search,
        to: paperId ? `/workspaces/${workspaceId}/projects/${projectId}/papers/${paperId}/similar` : undefined,
        inert: !paperId,
      },
    ],
  },
  {
    label: "AI Writing",
    items: [
      {
        label: "Draft Generation",
        icon: Sparkles,
        to: projectId ? `/workspaces/${workspaceId}/projects/${projectId}/drafts/generate` : undefined,
        inert: !projectId,
      },
      {
        label: "Draft Review",
        icon: PenTool,
        to: projectId ? `/workspaces/${workspaceId}/projects/${projectId}/drafts/review` : undefined,
        inert: !projectId,
      },
    ],
  },
];

export default function Sidebar({ workspaceId }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { projectId, paperId } = useParams();
  const sections = SECTIONS(workspaceId, projectId, paperId);

  return (
    <aside className="flex h-screen w-[228px] shrink-0 flex-col bg-sidebar">
      <button
        type="button"
        onClick={() => navigate("/dashboard")}
        className="flex items-center gap-2.5 px-5 pb-4 pt-6 text-left"
      >
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent shadow-[0_8px_24px_-4px_rgba(124,58,237,0.35)]">
          <FileText size={16} color="#fff" strokeWidth={1.5} />
        </div>
        <span className="text-base font-bold tracking-tight text-white">PaperTrail</span>
      </button>

      <div className="px-4 pb-2">
        <button
          type="button"
          onClick={() => navigate("/workspaces")}
          className="flex w-full items-center gap-2.5 rounded-xl border border-white/[0.06] bg-white/5 px-3.5 py-2.5 text-left transition-colors hover:bg-white/[0.08]"
        >
          <Search size={13} className="text-white/30" strokeWidth={1.5} />
          <span className="flex-1 text-xs text-white/30">Search workspaces…</span>
        </button>
      </div>

      <nav className="no-scrollbar flex-1 overflow-auto px-3 pb-3 pt-2">
        {sections.map((section) => (
          <div key={section.label} className="mb-6">
            <p className="mb-1.5 ml-2 text-[10px] font-bold uppercase tracking-wider text-white/22">
              {section.label}
            </p>
            {section.items.map((item) => {
              const active = !item.inert && location.pathname === item.to;
              return (
                <button
                  key={item.label}
                  type="button"
                  disabled={item.inert}
                  onClick={() => !item.inert && navigate(item.to)}
                  className={`mb-0.5 flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-left text-[13.5px] transition-colors ${
                    active
                      ? "bg-sidebar-active font-semibold text-[#DDD6FE]"
                      : item.inert
                        ? "cursor-default text-white/25"
                        : "text-white/50 hover:bg-sidebar-hover hover:text-white/80"
                  }`}
                >
                  <item.icon size={15} strokeWidth={active ? 2 : 1.5} />
                  {item.label}
                </button>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="border-t border-white/[0.06] px-3 py-3">
        <button
          type="button"
          onClick={() => navigate("/settings")}
          className={`flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-left text-[13.5px] transition-colors ${
            location.pathname === "/settings"
              ? "bg-sidebar-active font-semibold text-[#DDD6FE]"
              : "text-white/50 hover:bg-sidebar-hover hover:text-white/80"
          }`}
        >
          <Settings size={15} strokeWidth={location.pathname === "/settings" ? 2 : 1.5} />
          Settings
        </button>
      </div>
    </aside>
  );
}
