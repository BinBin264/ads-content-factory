import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import HomePage from "./pages/HomePage";
import ProjectDetailPage from "./pages/ProjectDetailPage";

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/projects/:id" element={<ProjectDetailPage phase="brief" />} />
          <Route path="/projects/:id/brief" element={<ProjectDetailPage phase="brief" />} />
          <Route path="/projects/:id/assets" element={<ProjectDetailPage phase="brief" />} />
          <Route path="/projects/:id/plan-creation" element={<ProjectDetailPage phase="plan-creation" />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
