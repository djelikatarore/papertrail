// The backend's Project model has no color field — derive a stable color per
// project from its id so cards look distinct without needing backend changes
// just for a cosmetic accent. 12 colors spaced ~25-45° apart around the hue
// wheel (all Tailwind-500-class saturation/lightness, matching the existing
// accent/teal/green/amber/red vividness) so neighboring projects rarely land
// on visually-confusable colors, unlike the old 5-color palette which
// repeated every 5 projects.
const PALETTE = [
  { name: "accent", hex: "#7C3AED" },
  { name: "teal", hex: "#0D9488" },
  { name: "green", hex: "#10B981" },
  { name: "amber", hex: "#F59E0B" },
  { name: "red", hex: "#EF4444" },
  { name: "orange", hex: "#F97316" },
  { name: "lime", hex: "#65A30D" },
  { name: "cyan", hex: "#06B6D4" },
  { name: "blue", hex: "#3B82F6" },
  { name: "indigo", hex: "#6366F1" },
  { name: "fuchsia", hex: "#D946EF" },
  { name: "pink", hex: "#EC4899" },
];

export function getProjectColor(projectId) {
  return PALETTE[projectId % PALETTE.length];
}
