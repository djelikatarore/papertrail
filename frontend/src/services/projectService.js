import apiClient from "./apiClient";

export function createProject(workspaceId, { title, topic, description }) {
  return apiClient
    .post(`/workspaces/${workspaceId}/projects`, { title, topic, description })
    .then((res) => res.data);
}

export function getProject(workspaceId, projectId) {
  return apiClient.get(`/workspaces/${workspaceId}/projects/${projectId}`).then((res) => res.data);
}

export function updateProject(workspaceId, projectId, { title, topic, description }) {
  return apiClient
    .put(`/workspaces/${workspaceId}/projects/${projectId}`, { title, topic, description })
    .then((res) => res.data);
}

export function deleteProject(workspaceId, projectId) {
  return apiClient.delete(`/workspaces/${workspaceId}/projects/${projectId}`);
}

export function askComparative(workspaceId, projectId, { question, paperIds }) {
  return apiClient
    .post(`/workspaces/${workspaceId}/projects/${projectId}/ask-comparative`, {
      question,
      paper_ids: paperIds,
    })
    .then((res) => res.data);
}

export function getProjectChatHistory(workspaceId, projectId) {
  return apiClient
    .get(`/workspaces/${workspaceId}/projects/${projectId}/chat-history`)
    .then((res) => res.data);
}

export function getCitationGraph(workspaceId, projectId) {
  return apiClient
    .get(`/workspaces/${workspaceId}/projects/${projectId}/citation-graph`)
    .then((res) => res.data);
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
