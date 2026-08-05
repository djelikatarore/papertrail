// The draft-generation prompt always asks the model for "## Section Name"
// Markdown headers (see backend/app/services/draft_generation_service.py::
// _build_draft_prompt) — splitting on that real structure lets a draft's
// content render as one card per section (Draft Generation results, Draft
// Review content) without inventing any section data that isn't actually in
// draft.content. Shared so both screens render the same draft the same way.
export function splitIntoSections(content) {
  if (!content) return [];
  const matches = [...content.matchAll(/^##\s+(.+)$/gm)];
  if (matches.length === 0) return [{ title: null, body: content.trim() }];

  return matches.map((match, i) => {
    const start = match.index + match[0].length;
    const end = i + 1 < matches.length ? matches[i + 1].index : content.length;
    return { title: match[1].trim(), body: content.slice(start, end).trim() };
  });
}
