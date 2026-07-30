import { AlertTriangle } from "lucide-react";

export default function NonAcademicWarningBanner({ contentWarning }) {
  if (!contentWarning) return null;

  return (
    <div className="flex items-start gap-2 rounded-lg bg-amber-light px-4 py-3 text-sm text-amber">
      <AlertTriangle size={16} className="mt-0.5 shrink-0" />
      <span>{contentWarning}</span>
    </div>
  );
}
