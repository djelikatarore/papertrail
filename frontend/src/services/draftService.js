import apiClient from "./apiClient";

const base = (workspaceId, projectId) => `/workspaces/${workspaceId}/projects/${projectId}/drafts`;

export function listDrafts(workspaceId, projectId) {
  return apiClient.get(base(workspaceId, projectId)).then((res) => res.data);
}

export function createDraft(workspaceId, projectId, { title, documentType, content }) {
  return apiClient
    .post(base(workspaceId, projectId), { title, document_type: documentType, content })
    .then((res) => res.data);
}

export function getDraft(workspaceId, projectId, draftId) {
  return apiClient.get(`${base(workspaceId, projectId)}/${draftId}`).then((res) => res.data);
}

export function generateDraft(workspaceId, projectId, { documentType, paperIds }) {
  return apiClient
    .post(`${base(workspaceId, projectId)}/generate`, { document_type: documentType, paper_ids: paperIds })
    .then((res) => res.data);
}

export function updateDraft(workspaceId, projectId, draftId, { title, content } = {}) {
  const payload = {};
  if (title !== undefined) payload.title = title;
  if (content !== undefined) payload.content = content;
  return apiClient.put(`${base(workspaceId, projectId)}/${draftId}`, payload).then((res) => res.data);
}

export function deleteDraft(workspaceId, projectId, draftId) {
  return apiClient.delete(`${base(workspaceId, projectId)}/${draftId}`);
}

export function createReviewComment(workspaceId, projectId, draftId, content) {
  return apiClient
    .post(`${base(workspaceId, projectId)}/${draftId}/comments`, { content })
    .then((res) => res.data);
}

export function deleteReviewComment(workspaceId, projectId, draftId, commentId) {
  return apiClient.delete(`${base(workspaceId, projectId)}/${draftId}/comments/${commentId}`);
}

// A plain <a href> can't attach the JWT the download endpoint requires —
// fetch the bytes via apiClient (which does attach it) and trigger the save
// through a throwaway object URL, same approach as AuthenticatedImage.
export async function downloadDraftPdf(workspaceId, projectId, draft) {
  const res = await apiClient.get(`${base(workspaceId, projectId)}/${draft.id}/download`, {
    responseType: "blob",
  });
  const url = URL.createObjectURL(res.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${draft.title}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function listReviewComments(workspaceId, projectId, draftId) {
  return apiClient.get(`${base(workspaceId, projectId)}/${draftId}/comments`).then((res) => res.data);
}

export function updateReviewComment(workspaceId, projectId, draftId, commentId, { status }) {
  return apiClient
    .put(`${base(workspaceId, projectId)}/${draftId}/comments/${commentId}`, { status })
    .then((res) => res.data);
}

export function submitDraftFeedback(workspaceId, projectId, draftId, { feedbackText, feedbackFile }) {
  const formData = new FormData();
  if (feedbackFile) {
    formData.append("feedback_file", feedbackFile);
  } else {
    formData.append("feedback_text", feedbackText);
  }

  return apiClient
    .post(`${base(workspaceId, projectId)}/${draftId}/feedback`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    .then((res) => res.data);
}
