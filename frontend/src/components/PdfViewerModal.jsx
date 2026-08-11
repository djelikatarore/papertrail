import { useEffect, useState } from "react";
import ErrorBanner from "./ErrorBanner";
import Modal from "./Modal";
import { getPaperPdfObjectUrl } from "../services/paperService";

// Fetches the PDF as an authenticated blob (same constraint as
// downloadPaperPdf — the /download endpoint needs a JWT a plain <iframe
// src="/api/..."> can't attach) and renders it inline via object URL.
export default function PdfViewerModal({ paper, onClose }) {
  const [objectUrl, setObjectUrl] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    let url = null;
    getPaperPdfObjectUrl(paper.id)
      .then((u) => {
        if (cancelled) {
          URL.revokeObjectURL(u);
          return;
        }
        url = u;
        setObjectUrl(u);
      })
      .catch(() => setError("Could not load this PDF. Please try again."));
    return () => {
      cancelled = true;
      if (url) URL.revokeObjectURL(url);
    };
  }, [paper.id]);

  return (
    <Modal onClose={onClose} maxWidth="max-w-4xl">
      <h3 className="mb-4 pr-6 text-lg font-bold text-text">{paper.title ?? paper.filename}</h3>
      {error ? (
        <ErrorBanner message={error} />
      ) : objectUrl ? (
        <iframe src={objectUrl} title="PDF viewer" className="h-[75vh] w-full rounded-lg border border-border" />
      ) : (
        <div className="flex h-[75vh] items-center justify-center text-sm text-muted">Loading PDF...</div>
      )}
    </Modal>
  );
}
