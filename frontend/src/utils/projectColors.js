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

// Takes the item's POSITION in the currently-rendered list, not its raw
// database id. Real ids are sparse (workspace/project ids in this app can
// easily be e.g. 84, 96, ...) so id % PALETTE.length collided far too often
// in practice — two cards sitting right next to each other would land on
// the exact same color whenever their ids happened to differ by a multiple
// of PALETTE.length. Position-based assignment guarantees every card
// visible together in the same grid/list gets a distinct color (as long as
// there are 12 or fewer of them on screen at once, true for every grid/list
// in this app today).
export function getProjectColor(index) {
  return PALETTE[index % PALETTE.length];
}
