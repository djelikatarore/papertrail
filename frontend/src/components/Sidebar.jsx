import {
  BookOpen,
  FileText,
  FolderOpen,
  LayoutDashboard,
  MessageSquare,
  PenTool,
  Search,
  Sparkles,
  Upload,
} from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

const SECTIONS = (workspaceId) => [
  {
    label: "Workspace",
    items: [
      { label: "Dashboard", icon: LayoutDashboard, to: "/dashboard" },
      { label: "Projects", icon: FolderOpen, to: `/workspaces/${workspaceId}` },
    ],
  },
  {
    label: "Paper Tools",
    items: [
      { label: "Upload Paper", icon: Upload, inert: true },
      { label: "AI Chat", icon: MessageSquare, inert: true },
      { label: "Similar Papers", icon: Search, inert: true },
    ],
  },
  {
    label: "AI Writing",
    items: [
      { label: "Draft Generation", icon: Sparkles, inert: true },
      { label: "Draft Review", icon: PenTool, inert: true },
    ],
  },
];

export default function Sidebar({ workspaceId }) {
  const location = useLocation();
  const navigate = useNavigate();
  const sections = SECTIONS(workspaceId);

  return (
    <aside className="flex h-screen w-[228px] shrink-0 flex-col bg-sidebar">
      <div className="flex items-center gap-2.5 px-5 pb-4 pt-6">
        <div className="flex h-8 w-8 items-center justify-center rounded-[9px] bg-accent">
          <FileText size={15} color="#fff" strokeWidth={1.5} />
        </div>
        <span className="text-base font-bold tracking-tight text-white">PaperTrail</span>
      </div>

      <nav className="flex-1 overflow-auto px-3 pb-5 pt-2">
        {sections.map((section) => (
          <div key={section.label} className="mb-6">
            <p className="mb-1.5 ml-2 text-[10px] font-bold uppercase tracking-wider text-white/28">
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
                  className={`mb-0.5 flex w-full items-center gap-2.5 rounded-[9px] px-2.5 py-2 text-left text-[13.5px] transition-colors ${
                    active
                      ? "bg-sidebar-active font-semibold text-[#DDD6FE]"
                      : item.inert
                        ? "cursor-default text-white/25"
                        : "text-white/50 hover:text-white/80"
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
    </aside>
  );
}
