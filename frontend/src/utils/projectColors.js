// The backend's Project model has no color field — derive a stable color per
// project from its id so cards look distinct without needing backend changes
// just for a cosmetic accent.
const PALETTE = [
  { name: "accent", hex: "#7C3AED" },
  { name: "teal", hex: "#0D9488" },
  { name: "green", hex: "#10B981" },
  { name: "amber", hex: "#F59E0B" },
  { name: "red", hex: "#EF4444" },
];

export function getProjectColor(projectId) {
  return PALETTE[projectId % PALETTE.length];
}
