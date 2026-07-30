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
