import { FolderOpen } from "lucide-react";
import { getProjectColor } from "../utils/projectColors";

export default function ProjectCard({ project, onClick }) {
  const color = getProjectColor(project.id);

  return (
    <button
      type="button"
      onClick={onClick}
      className="overflow-hidden rounded-[var(--radius-card-lg)] border border-border bg-card text-left shadow-card transition-shadow hover:shadow-card-hover"
    >
      <div className="h-1" style={{ background: color.hex }} />
      <div className="p-6">
        <div
          className="mb-3.5 flex h-[42px] w-[42px] items-center justify-center rounded-xl"
          style={{ background: `${color.hex}18` }}
        >
          <FolderOpen size={20} color={color.hex} strokeWidth={1.5} />
        </div>
        <h3 className="mb-1.5 text-[15px] font-bold text-text">{project.title}</h3>
        <p className="mb-4 text-[13px] leading-snug text-muted">{project.topic}</p>
        <div className="flex items-center justify-between">
          <span
            className="rounded-full px-2.5 py-0.5 text-[11px] font-semibold"
            style={{ background: `${color.hex}18`, color: color.hex }}
          >
            {project.status ?? "Active"}
          </span>
        </div>
      </div>
    </button>
  );
}
