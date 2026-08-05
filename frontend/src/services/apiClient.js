import axios from "axios";
import { clearToken, getToken } from "./tokenStore";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});

apiClient.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// A 401 from any *authenticated* endpoint means the token we attached was
// missing/expired/invalid — the session itself is no longer valid, not
// something each page should silently swallow into a generic "could not
// load" message. /auth/login is exempt: its own 401 means the credentials
// just submitted were wrong, which is LoginPage's own error to show — not a
// session expiry.
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const isLoginRequest = error.config?.url?.includes("/auth/login");
    if (error.response?.status === 401 && !isLoginRequest) {
      clearToken();
      if (!window.location.pathname.startsWith("/login")) {
        window.location.href = "/login?sessionExpired=1";
      }
    }
    return Promise.reject(error);
  },
);

export default apiClient;
