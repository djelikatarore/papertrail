import { Layers, Pencil, Trash2 } from "lucide-react";
import { getProjectColor } from "../utils/projectColors";

// Same visual pattern as ProjectCard — color derived from the card's
// position in the current list, not its id (see getProjectColor).
// onRename/onDelete are optional (only the owner can act on a workspace, so
// a caller viewing a workspace they don't own simply omits them, same as
// PaperCard's optional onDelete).
export default function WorkspaceCard({ workspace, index = 0, active, onClick, onRename, onDelete }) {
  const color = getProjectColor(index);
  const isOwner = workspace.role === "OWNER";

  return (
    <button
      type="button"
      onClick={onClick}
      className={`overflow-hidden rounded-[var(--radius-card-lg)] border bg-card text-left shadow-card transition-shadow hover:shadow-card-hover ${
        active ? "border-accent ring-1 ring-accent" : "border-border"
      }`}
    >
      <div className="h-1" style={{ background: color.hex }} />
      <div className="p-6">
        <div className="mb-3.5 flex items-start justify-between">
          <div
            className="flex h-[42px] w-[42px] items-center justify-center rounded-xl"
            style={{ background: `${color.hex}18` }}
          >
            <Layers size={20} color={color.hex} strokeWidth={1.5} />
          </div>
          {isOwner && (onRename || onDelete) && (
            <div className="flex gap-1">
              {onRename && (
                <button
                  type="button"
                  aria-label="Rename workspace"
                  onClick={(e) => {
                    e.stopPropagation();
                    onRename(workspace);
                  }}
                  className="rounded-md p-1.5 text-muted transition-colors hover:bg-accent-light hover:text-accent"
                >
                  <Pencil size={13} />
                </button>
              )}
              {onDelete && (
                <button
                  type="button"
                  aria-label="Delete workspace"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(workspace);
                  }}
                  className="rounded-md p-1.5 text-muted transition-colors hover:bg-red-light hover:text-red"
                >
                  <Trash2 size={13} />
                </button>
              )}
            </div>
          )}
        </div>
        <h3 className="mb-1.5 truncate text-[15px] font-bold text-text">{workspace.name}</h3>
        {workspace.description && (
          <p className="mb-4 line-clamp-2 text-[13px] leading-snug text-muted">{workspace.description}</p>
        )}
        <div className="flex items-center justify-between">
          <span
            className="rounded-full px-2.5 py-0.5 text-[11px] font-semibold"
            style={{ background: `${color.hex}18`, color: color.hex }}
          >
            {workspace.role}
          </span>
          {active && <span className="text-[11px] font-semibold text-accent">Current</span>}
        </div>
      </div>
    </button>
  );
}
