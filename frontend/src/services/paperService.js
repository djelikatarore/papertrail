import apiClient from "./apiClient";

export function getPaper(paperId) {
  return apiClient.get(`/papers/${paperId}`).then((res) => res.data);
}

// Lightweight (id/title/filename/status only) — powers the app-wide
// "notify me when a paper is ready" watcher, which polls this on an
// interval no matter which screen is open. Scoped server-side to papers the
// current user uploaded that are still PROCESSING.
export function listMyProcessingPapers() {
  return apiClient.get("/papers/mine/processing").then((res) => res.data);
}

export function listProjectPapers(workspaceId, projectId, { page = 1, limit = 20 } = {}) {
  return apiClient
    .get(`/workspaces/${workspaceId}/projects/${projectId}/papers`, { params: { page, limit } })
    .then((res) => res.data);
}

export function askQuestion(paperId, question) {
  return apiClient.post(`/papers/${paperId}/ask`, { question }).then((res) => res.data);
}

export function getPaperChatHistory(paperId) {
  return apiClient.get(`/papers/${paperId}/chat-history`).then((res) => res.data);
}

// Same approach as draftService.downloadDraftPdf — a plain <a href> can't
// attach the JWT this endpoint requires, so fetch the bytes via apiClient
// and trigger the save through a throwaway object URL.
export async function downloadPaperPdf(paper) {
  const url = await getPaperPdfObjectUrl(paper.id);
  const link = document.createElement("a");
  link.href = url;
  link.download = paper.filename ?? `${paper.id}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

// Same JWT constraint as downloadPaperPdf, but for callers that want to keep
// the object URL around (new-tab viewing, inline <iframe>) instead of
// triggering an immediate download+revoke. Caller is responsible for
// revoking the URL once it's no longer needed.
export async function getPaperPdfObjectUrl(paperId) {
  const res = await apiClient.get(`/papers/${paperId}/download`, { responseType: "blob" });
  return URL.createObjectURL(res.data);
}

export function deletePaper(paperId) {
  return apiClient.delete(`/papers/${paperId}`);
}

export function uploadPaper({ workspaceId, projectId, reviewType, file }) {
  const formData = new FormData();
  formData.append("workspace_id", workspaceId);
  formData.append("project_id", projectId);
  formData.append("review_type", reviewType);
  formData.append("file", file);

  return apiClient
    .post("/papers/upload", formData, { headers: { "Content-Type": "multipart/form-data" } })
    .then((res) => res.data);
}
