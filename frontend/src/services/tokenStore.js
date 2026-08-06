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

// Fires when a DIFFERENT tab/window changes the token in localStorage (login,
// logout, or switching accounts there) — the same-tab setToken/clearToken
// calls above don't trigger the browser's `storage` event at all, only other
// tabs do. Without this, a tab left open through another tab's logout keeps
// its in-memory `currentToken` (and therefore every request it makes) on the
// old session indefinitely, even though the user believes they're logged out.
export function onTokenChangedExternally(callback) {
  function handleStorage(event) {
    if (event.key !== STORAGE_KEY) return;
    currentToken = event.newValue;
    callback(event.newValue);
  }
  window.addEventListener("storage", handleStorage);
  return () => window.removeEventListener("storage", handleStorage);
}
