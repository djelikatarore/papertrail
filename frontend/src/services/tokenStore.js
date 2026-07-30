// Holds the current JWT outside of React so non-component modules (like the
// axios client) can read it synchronously on every request, without needing
// to be inside a component tree. AuthContext is the only thing that should
// call setToken/clearToken — everything else should just read via getToken.
//
// Persisted to localStorage so a page refresh doesn't log the user out —
// the in-memory variable is just a synchronous-read cache on top of it.
const STORAGE_KEY = "papertrail_token";

let currentToken = localStorage.getItem(STORAGE_KEY);

export function getToken() {
  return currentToken;
}

export function setToken(token) {
  currentToken = token;
  localStorage.setItem(STORAGE_KEY, token);
}

export function clearToken() {
  currentToken = null;
  localStorage.removeItem(STORAGE_KEY);
}
