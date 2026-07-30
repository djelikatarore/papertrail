// Holds the current JWT outside of React so non-component modules (like the
// axios client) can read it synchronously on every request, without needing
// to be inside a component tree. AuthContext is the only thing that should
// call setToken/clearToken — everything else should just read via getToken.
let currentToken = null;

export function getToken() {
  return currentToken;
}

export function setToken(token) {
  currentToken = token;
}

export function clearToken() {
  currentToken = null;
}
