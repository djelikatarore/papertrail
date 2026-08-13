import apiClient from "./apiClient";

export function signup({ fullName, email, password, inviteToken }) {
  return apiClient
    .post("/auth/signup", { full_name: fullName, email, password, invite_token: inviteToken ?? null })
    .then((res) => res.data);
}

export function login({ email, password }) {
  return apiClient.post("/auth/login", { email, password }).then((res) => res.data);
}

// idToken is the raw signed JWT handed back by Google Identity Services in
// the browser — the backend verifies it against Google's own public keys
// (see POST /auth/google), not just its shape.
export function loginWithGoogle(idToken) {
  return apiClient.post("/auth/google", { id_token: idToken }).then((res) => res.data);
}

export function getCurrentUser() {
  return apiClient.get("/auth/me").then((res) => res.data);
}

export function updateProfile({ fullName }) {
  return apiClient.put("/auth/me", { full_name: fullName }).then((res) => res.data);
}

export function forgotPassword(email) {
  return apiClient.post("/auth/forgot-password", { email }).then((res) => res.data);
}

export function resetPassword({ token, newPassword }) {
  return apiClient
    .post("/auth/reset-password", { token, new_password: newPassword })
    .then((res) => res.data);
}

export function verifyEmail(token) {
  return apiClient.get("/auth/verify-email", { params: { token } }).then((res) => res.data);
}
