import apiClient from "./apiClient";

export function createWorkspace({ name, description }) {
  return apiClient.post("/workspaces", { name, description }).then((res) => res.data);
}

export function listWorkspaces() {
  return apiClient.get("/workspaces").then((res) => res.data);
}

export function updateWorkspace(workspaceId, { name, description }) {
  return apiClient.put(`/workspaces/${workspaceId}`, { name, description }).then((res) => res.data);
}

export function deleteWorkspace(workspaceId) {
  return apiClient.delete(`/workspaces/${workspaceId}`);
}

export function listMembers(workspaceId) {
  return apiClient.get(`/workspaces/${workspaceId}/members`).then((res) => res.data);
}

export function removeMember(workspaceId, memberId) {
  return apiClient.delete(`/workspaces/${workspaceId}/members/${memberId}`);
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

export function getInviteLink(workspaceId) {
  return apiClient.get(`/workspaces/${workspaceId}/invite-link`).then((res) => res.data);
}

export function inviteByEmail(workspaceId, email) {
  return apiClient.post(`/workspaces/${workspaceId}/invite`, { email }).then((res) => res.data);
}

export function getInvitationPreview(token) {
  return apiClient.get(`/workspaces/invitations/${token}`).then((res) => res.data);
}

export function acceptInvitation(token) {
  return apiClient.post(`/workspaces/invitations/${token}/accept`).then((res) => res.data);
}

export function joinWorkspace(token) {
  return apiClient.post(`/workspaces/join/${token}`).then((res) => res.data);
}
