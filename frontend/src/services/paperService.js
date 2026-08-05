import apiClient from "./apiClient";

export function getPaper(paperId) {
  return apiClient.get(`/papers/${paperId}`).then((res) => res.data);
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
  const res = await apiClient.get(`/papers/${paper.id}/download`, { responseType: "blob" });
  const url = URL.createObjectURL(res.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = paper.filename ?? `${paper.id}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
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
