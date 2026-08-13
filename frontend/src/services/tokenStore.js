// Holds the current JWT outside of React so non-component modules (like the
// axios client) can read it synchronously on every request, without needing
// to be inside a component tree. AuthContext is the only thing that should
// call setToken/clearToken — everything else should just read via getToken.
//
// "Remember me" controls WHICH storage backs it: localStorage survives
// closing the browser (a real refresh doesn't log the user out either way,
// since both storages persist across reloads within the same tab/browser
// session) while sessionStorage is cleared as soon as the browser/tab
// closes. Only one of the two ever holds the token at a time — the other is
// actively cleared on every write so a stale copy can't resurrect a session
// the user didn't ask to keep.
const STORAGE_KEY = "papertrail_token";

let currentToken = localStorage.getItem(STORAGE_KEY) ?? sessionStorage.getItem(STORAGE_KEY);

export function getToken() {
  return currentToken;
}

export function setToken(token, remember = true) {
  currentToken = token;
  if (remember) {
    localStorage.setItem(STORAGE_KEY, token);
    sessionStorage.removeItem(STORAGE_KEY);
  } else {
    sessionStorage.setItem(STORAGE_KEY, token);
    localStorage.removeItem(STORAGE_KEY);
  }
}

export function clearToken() {
  currentToken = null;
  localStorage.removeItem(STORAGE_KEY);
  sessionStorage.removeItem(STORAGE_KEY);
}

// Separate from the session token on purpose: this is only the last email
// used with "Remember me" checked, so LoginPage can pre-fill it — it must
// survive an explicit Logout (which wipes the token above) since that's the
// whole point of remembering it, and it never holds anything sensitive like
// a password or token.
const REMEMBERED_EMAIL_KEY = "papertrail_remembered_email";

export function getRememberedEmail() {
  return localStorage.getItem(REMEMBERED_EMAIL_KEY) ?? "";
}

export function setRememberedEmail(email) {
  localStorage.setItem(REMEMBERED_EMAIL_KEY, email);
}

export function clearRememberedEmail() {
  localStorage.removeItem(REMEMBERED_EMAIL_KEY);
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
