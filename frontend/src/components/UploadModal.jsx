import { CheckCircle, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { uploadPaper } from "../services/paperService";
import ErrorBanner from "./ErrorBanner";
import Modal from "./Modal";

const REVIEW_TYPES = [
  { value: "SYSTEMATIC", label: "Systematic" },
  { value: "SCOPING", label: "Scoping" },
  { value: "CRITICAL", label: "Critical" },
  { value: "NARRATIVE", label: "Narrative" },
  { value: "RAPID", label: "Rapid" },
];

const PDF_SIGNATURE = "%PDF-";

export default function UploadModal({ workspaceId, projectId, onClose, onUploaded }) {
  const [step, setStep] = useState("file");
  const [file, setFile] = useState(null);
  const [fileError, setFileError] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [reviewType, setReviewType] = useState("SYSTEMATIC");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  // Validated the moment a file is picked/dropped, not left until the final
  // "Upload" click — a wrong extension or a corrupted/mislabeled PDF (checked
  // via its actual %PDF- header, not just the filename) is caught here
  // instead of only surfacing as a vague backend error after the user has
  // already stepped past this screen.
  function validateAndSetFile(selected) {
    setFile(null);
    setFileError(null);
    if (!selected) return;

    const looksLikePdf = selected.type === "application/pdf" || selected.name.toLowerCase().endsWith(".pdf");
    if (!looksLikePdf) {
      setFileError("Please select a PDF file.");
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const bytes = new Uint8Array(reader.result);
      const header = String.fromCharCode(...bytes);
      if (header !== PDF_SIGNATURE) {
        setFileError("This file doesn't look like a valid PDF.");
        return;
      }
      setFile(selected);
    };
    reader.onerror = () => setFileError("Could not read this file. Please try again.");
    reader.readAsArrayBuffer(selected.slice(0, PDF_SIGNATURE.length));
  }

  function handleDrop(event) {
    event.preventDefault();
    setDragging(false);
    validateAndSetFile(event.dataTransfer.files[0]);
  }

  async function handleUpload() {
    setSubmitting(true);
    setError(null);
    try {
      await uploadPaper({ workspaceId, projectId, reviewType, file });
      onUploaded();
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail ?? "Upload failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal onClose={onClose}>
      <div className="mb-6 flex items-center gap-2 pr-6">
        {["file", "review"].map((s, i) => (
          <div
            key={s}
            className={`flex h-[22px] w-[22px] items-center justify-center rounded-full text-[10px] font-bold ${
              ["file", "review"].indexOf(step) >= i ? "bg-accent text-white" : "bg-border text-muted"
            }`}
          >
            {i + 1}
          </div>
        ))}
      </div>

      {step === "file" && (
        <>
          <h3 className="mb-1.5 text-lg font-bold text-text">Select a paper</h3>
          <p className="mb-5 text-sm text-muted">Upload a PDF or drag and drop</p>
          <div
            onDrop={handleDrop}
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onClick={() => fileInputRef.current?.click()}
            className={`cursor-pointer rounded-2xl border-2 border-dashed p-9 text-center transition-colors ${
              dragging ? "border-accent bg-accent-light" : "border-border bg-app-bg"
            }`}
          >
            <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-accent-light">
              <Upload size={22} className="text-accent" strokeWidth={1.5} />
            </div>
            <p className="mb-1 text-sm font-semibold text-text">Drag & drop your PDF here</p>
            <p className="text-sm text-muted">or click to browse files</p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={(e) => validateAndSetFile(e.target.files?.[0] ?? null)}
            />
          </div>
          {file && (
            <div className="mt-3 flex items-center gap-2 rounded-xl bg-green-light px-3.5 py-2.5 text-sm font-medium text-green">
              <CheckCircle size={14} /> {file.name}
            </div>
          )}
          {fileError && (
            <div className="mt-3">
              <ErrorBanner message={fileError} />
            </div>
          )}
          <div className="mt-5 flex gap-2.5">
            <button type="button" onClick={onClose} className="btn-secondary flex-1 py-2.5">
              Cancel
            </button>
            <button
              type="button"
              disabled={!file}
              onClick={() => setStep("review")}
              className="btn-primary flex-1 py-2.5"
            >
              Next
            </button>
          </div>
        </>
      )}

      {step === "review" && (
        <>
          <h3 className="mb-1.5 text-lg font-bold text-text">Review type</h3>
          <p className="mb-5 text-sm text-muted">How will this paper be used in your review?</p>
          <div className="grid grid-cols-2 gap-2">
            {REVIEW_TYPES.map((rt) => (
              <button
                key={rt.value}
                type="button"
                onClick={() => setReviewType(rt.value)}
                className={`rounded-xl border px-3.5 py-3 text-left transition-colors ${
                  reviewType === rt.value
                    ? "border-accent bg-accent-light"
                    : "border-border bg-card hover:border-accent/30"
                }`}
              >
                <p className="text-sm font-bold text-text">{rt.label}</p>
              </button>
            ))}
          </div>
          {error && (
            <div className="mt-4">
              <ErrorBanner message={error} />
            </div>
          )}
          <div className="mt-5 flex gap-2.5">
            <button type="button" onClick={() => setStep("file")} className="btn-secondary flex-1 py-2.5">
              Back
            </button>
            <button
              type="button"
              disabled={submitting}
              onClick={handleUpload}
              className="btn-primary flex-1 py-2.5"
            >
              {submitting ? "Uploading..." : "Upload"}
            </button>
          </div>
        </>
      )}
    </Modal>
  );
}
