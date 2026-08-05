import { ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";
import AvatarMenu from "./AvatarMenu";
import Sidebar from "./Sidebar";

// Every screen gets a back button by default (navigate(-1) — real browser
// history, not a hardcoded parent route), except Dashboard which explicitly
// passes showBack={false} since it's the app's home. A page can still pass
// its own `onBack` to override the default when it needs to (e.g. Draft
// Review stepping back from "reviewing a draft" to "picking a draft" without
// leaving the screen).
export default function AppShell({ workspaceId, title, subtitle, onBack, showBack = true, children }) {
  const navigate = useNavigate();
  const handleBack = onBack ?? (() => navigate(-1));

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar workspaceId={workspaceId} />
      <div className="flex flex-1 flex-col overflow-hidden bg-app-bg">
        <div className="flex shrink-0 items-start justify-between px-10 pt-5">
          <div>
            {showBack && (
              <button
                type="button"
                onClick={handleBack}
                className="mb-2 flex items-center gap-1.5 text-sm font-medium text-muted transition-colors hover:text-text"
              >
                <ArrowLeft size={14} /> Back
              </button>
            )}
            <h1 className="text-[22px] font-bold tracking-tight text-text">{title}</h1>
            {subtitle && <p className="mt-0.5 text-sm text-muted">{subtitle}</p>}
          </div>
          <AvatarMenu />
        </div>
        <div className="flex-1 overflow-auto">{children}</div>
      </div>
    </div>
  );
}
