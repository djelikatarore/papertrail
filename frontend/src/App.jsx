import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import DashboardPage from "./pages/DashboardPage";
import DraftGenerationPage from "./pages/DraftGenerationPage";
import DraftReviewPage from "./pages/DraftReviewPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import LoginPage from "./pages/LoginPage";
import PaperDetailsPage from "./pages/PaperDetailsPage";
import ProjectPage from "./pages/ProjectPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import SearchPage from "./pages/SearchPage";
import SignupPage from "./pages/SignupPage";
import WorkspacePage from "./pages/WorkspacePage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />

      <Route element={<ProtectedRoute />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/workspaces/:workspaceId" element={<WorkspacePage />} />
        <Route
          path="/workspaces/:workspaceId/projects/:projectId"
          element={<ProjectPage />}
        />
        <Route
          path="/workspaces/:workspaceId/projects/:projectId/papers/:paperId"
          element={<PaperDetailsPage />}
        />
        <Route
          path="/workspaces/:workspaceId/projects/:projectId/search"
          element={<SearchPage />}
        />
        <Route
          path="/workspaces/:workspaceId/projects/:projectId/drafts/review"
          element={<DraftReviewPage />}
        />
        <Route
          path="/workspaces/:workspaceId/projects/:projectId/drafts/generate"
          element={<DraftGenerationPage />}
        />
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
