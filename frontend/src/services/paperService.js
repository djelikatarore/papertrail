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
