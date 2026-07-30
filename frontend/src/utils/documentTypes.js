// Mirrors backend VALID_DOCUMENT_TYPES (backend/app/config/settings.py) — keep
// in sync manually since the frontend has no way to fetch it dynamically.
export const DOCUMENT_TYPES = [
  "LITERATURE_REVIEW",
  "RESEARCH_PROPOSAL",
  "THESIS_CHAPTER",
  "CONFERENCE_PAPER",
  "OTHER",
];

export const DOCUMENT_TYPE_LABELS = {
  LITERATURE_REVIEW: "Literature Review",
  RESEARCH_PROPOSAL: "Research Proposal",
  THESIS_CHAPTER: "Thesis Chapter",
  CONFERENCE_PAPER: "Conference Paper",
  OTHER: "Other",
};
