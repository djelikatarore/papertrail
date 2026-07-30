import apiClient from "./apiClient";

export function createWorkspace({ name, description }) {
  return apiClient.post("/workspaces", { name, description }).then((res) => res.data);
}

export function listWorkspaces() {
  return apiClient.get("/workspaces").then((res) => res.data);
}

export function listMembers(workspaceId) {
  return apiClient.get(`/workspaces/${workspaceId}/members`).then((res) => res.data);
}

export function listProjects(workspaceId, { page = 1, limit = 20 } = {}) {
  return apiClient
    .get(`/workspaces/${workspaceId}/projects`, { params: { page, limit } })
    .then((res) => res.data);
}

export function searchWorkspace(workspaceId, query) {
  return apiClient
    .get(`/workspaces/${workspaceId}/search`, { params: { q: query } })
    .then((res) => res.data);
}
