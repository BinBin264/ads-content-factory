import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Link, useNavigate } from "react-router-dom";
import ProjectForm from "../components/ProjectForm";
import { createProject, listProjects } from "../api/projects";
import { getApiErrorMessage } from "../api/client";
import type { CreateProjectValues, Project } from "../types";
import { compactId, formatDate } from "../utils/format";

export default function HomePage() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadProjects = async () => {
    try {
      setProjects(await listProjects());
    } catch (err) {
      setError(getApiErrorMessage(err));
    }
  };

  useEffect(() => {
    void loadProjects();
  }, []);

  const handleCreateProject = async (values: CreateProjectValues) => {
    setLoading(true);
    setError(null);
    try {
      const project = await createProject(values);
      navigate(`/projects/${project.id}/brief`);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const headerActions = document.getElementById("app-header-actions");

  return (
    <>
      {headerActions
        ? createPortal(
            <div className="header-workflow" aria-label="Production workflow">
              <div className="header-workflow-step is-active"><span>01</span><p>Brief</p></div>
              <i />
              <div className="header-workflow-step"><span>02</span><p>Plan</p></div>
              <i />
              <div className="header-workflow-step"><span>03</span><p>Keyframes</p></div>
              <i />
              <div className="header-workflow-step"><span>04</span><p>Clips</p></div>
            </div>,
            headerActions,
          )
        : null}
      <div className="home-page">
        <aside className="home-project-rail">
          <div className="home-rail-heading">
            <p className="home-eyebrow">Workspace</p>
            <h3>Projects</h3>
            <p>Start a new workflow or continue where you left off.</p>
          </div>

          <div className="home-new-project-item">
            <span>+</span>
            <div><strong>New project</strong><p>Define a fresh video brief</p></div>
          </div>

          <div className="home-recent-heading">
            <span>Recent projects</span>
            <button type="button" onClick={() => void loadProjects()}>Refresh</button>
          </div>

          <div className="home-project-list">
            {projects.length === 0 ? (
              <p className="home-empty-projects">No saved projects yet.</p>
            ) : (
              projects.map((project) => (
                <Link key={project.id} className="home-project-row" to={`/projects/${project.id}/brief`}>
                  <span className={project.workflow_type === "content_creation" ? "is-content" : "is-ads"}>
                    {project.workflow_type === "content_creation" ? "C" : "A"}
                  </span>
                  <div className="min-w-0 flex-1">
                    <strong className="truncate">{project.product_name}</strong>
                    <p>{project.product_category || "General"} / {compactId(project.id)}</p>
                    <small>{formatDate(project.updated_at)}</small>
                  </div>
                </Link>
              ))
            )}
          </div>
        </aside>

        <main className="home-editor">
          {error ? <div className="home-error">{error}</div> : null}
          <ProjectForm loading={loading} onSubmit={handleCreateProject} />
        </main>
      </div>
    </>
  );
}
