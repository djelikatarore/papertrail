import { Archive, CheckCircle, FolderOpen } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { getProjectColor } from "../utils/projectColors";

const STATUS_OPTIONS = [
  { value: "ACTIVE", label: "Active", icon: CheckCircle },
  { value: "ARCHIVED", label: "Archived", icon: Archive },
];

// Status is purely an organizational marker — an archived project keeps
// working exactly like an active one (upload, Q&A, everything). The only
// difference is visual: muted card + grey badge, so it still reads clearly
// in the same grid without needing a separate "Archived" section/filter.
export default function ProjectCard({ project, onClick, onStatusChange }) {
  const color = getProjectColor(project.id);
  const isArchived = project.status === "ARCHIVED";
  const [menuOpen, setMenuOpen] = useState(false);
  const [changing, setChanging] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  async function handleSelect(value) {
    setMenuOpen(false);
    if (value === project.status || changing || !onStatusChange) return;
    setChanging(true);
    try {
      await onStatusChange(project, value);
    } finally {
      setChanging(false);
    }
  }

  return (
    <button
      type="button"
      onClick={onClick}
      className={`overflow-hidden rounded-[var(--radius-card-lg)] border border-border bg-card text-left shadow-card transition-shadow hover:shadow-card-hover ${
        isArchived ? "opacity-55" : ""
      }`}
    >
      <div className="h-1" style={{ background: isArchived ? "var(--color-border)" : color.hex }} />
      <div className="p-6">
        <div
          className="mb-3.5 flex h-[42px] w-[42px] items-center justify-center rounded-xl"
          style={{ background: isArchived ? "var(--color-app-bg)" : `${color.hex}18` }}
        >
          <FolderOpen size={20} color={isArchived ? undefined : color.hex} className={isArchived ? "text-muted" : ""} strokeWidth={1.5} />
        </div>
        <h3 className="mb-1.5 text-[15px] font-bold text-text">{project.title}</h3>
        <p className="mb-4 text-[13px] leading-snug text-muted">{project.topic}</p>
        <div className="flex items-center justify-between">
          <div className="relative" ref={menuRef}>
            <span
              role="button"
              tabIndex={0}
              onClick={(e) => {
                e.stopPropagation();
                if (onStatusChange) setMenuOpen((v) => !v);
              }}
              onKeyDown={(e) => e.key === "Enter" && e.stopPropagation()}
              className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
                onStatusChange ? "cursor-pointer" : ""
              }`}
              style={
                isArchived
                  ? { background: "var(--color-border)", color: "var(--color-muted)" }
                  : { background: `${color.hex}18`, color: color.hex }
              }
            >
              {changing ? "..." : isArchived ? "Archived" : "Active"}
            </span>

            {menuOpen && (
              <div
                onClick={(e) => e.stopPropagation()}
                className="absolute left-0 top-[calc(100%+6px)] z-50 w-36 overflow-hidden rounded-xl border border-border bg-card shadow-card-hover"
              >
                {STATUS_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => handleSelect(opt.value)}
                    className={`flex w-full items-center gap-2 px-3 py-2 text-left text-xs transition-colors hover:bg-app-bg ${
                      project.status === opt.value ? "font-semibold text-text" : "text-muted"
                    }`}
                  >
                    <opt.icon size={13} /> {opt.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </button>
  );
}
