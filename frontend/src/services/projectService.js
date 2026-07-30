import apiClient from "./apiClient";

export function createProject(workspaceId, { title, topic, description }) {
  return apiClient
    .post(`/workspaces/${workspaceId}/projects`, { title, topic, description })
    .then((res) => res.data);
}

export function getProject(workspaceId, projectId) {
  return apiClient.get(`/workspaces/${workspaceId}/projects/${projectId}`).then((res) => res.data);
}

export function getProjectAccess(workspaceId, projectId) {
  return apiClient
    .get(`/workspaces/${workspaceId}/projects/${projectId}/access`)
    .then((res) => res.data);
}

export function updateProjectAccess(workspaceId, projectId, payload) {
  return apiClient
    .patch(`/workspaces/${workspaceId}/projects/${projectId}/access`, payload)
    .then((res) => res.data);
}

export function getSimilarity(workspaceId, projectId) {
  return apiClient
    .get(`/workspaces/${workspaceId}/projects/${projectId}/similarity`)
    .then((res) => res.data);
}

export function suggestPapers(workspaceId, projectId, { dateFrom, dateTo, category, author } = {}) {
  return apiClient
    .get(`/workspaces/${workspaceId}/projects/${projectId}/suggest-papers`, {
      params: {
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        category: category || undefined,
        author: author || undefined,
      },
    })
    .then((res) => res.data);
}
