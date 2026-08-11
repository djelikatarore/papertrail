// Same shape as ErrorBanner but amber instead of red — for a paper that's
// still READY and usable, just missing some AI-generated content (see
// Paper.processing_warning). A red ErrorBanner here would misread as "this
// paper is broken" when it isn't.
export default function WarningBanner({ message }) {
  if (!message) return null;

  return (
    <div className="rounded-lg bg-amber-light px-4 py-3 text-sm text-amber">
      {message}
    </div>
  );
}
