import { ArrowLeft } from "lucide-react";
import AvatarMenu from "./AvatarMenu";
import Sidebar from "./Sidebar";

export default function AppShell({ workspaceId, title, subtitle, onBack, children }) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar workspaceId={workspaceId} />
      <div className="flex flex-1 flex-col overflow-hidden bg-app-bg">
        <div className="flex shrink-0 items-start justify-between px-10 pt-5">
          <div>
            {onBack && (
              <button
                type="button"
                onClick={onBack}
                className="mb-2 flex items-center gap-1.5 text-sm font-medium text-muted"
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
