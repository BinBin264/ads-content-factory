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
          <Route path="/projects/:id/creative-plan" element={<ProjectDetailPage phase="creative-plan" />} />
          <Route path="/projects/:id/intelligence" element={<ProjectDetailPage phase="creative-plan" />} />
          <Route path="/projects/:id/angles" element={<ProjectDetailPage phase="variants" />} />
          <Route path="/projects/:id/variants" element={<ProjectDetailPage phase="variants" />} />
          <Route path="/projects/:id/production" element={<ProjectDetailPage phase="production" />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
