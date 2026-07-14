import { useEffect, useState } from "react";
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
      navigate(`/projects/${project.id}/plan-creation`);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1.25fr)_minmax(320px,0.75fr)]">
      <ProjectForm loading={loading} onSubmit={handleCreateProject} />

      <aside className="space-y-4">
        {error ? <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</div> : null}
        <section className="card-accent p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="section-heading">Projects</h2>
              <p className="section-subtitle">Recent local MVP projects.</p>
            </div>
            <button className="btn-secondary px-3 py-1 text-xs" type="button" onClick={() => void loadProjects()}>
              Refresh
            </button>
          </div>

          {projects.length === 0 ? (
            <p className="empty-state">No projects yet.</p>
          ) : (
            <div className="space-y-3">
              {projects.map((project) => (
                <Link
                  key={project.id}
                  className="block rounded-lg border border-slate-200 bg-white p-4 transition hover:-translate-y-0.5 hover:border-teal-300 hover:shadow-soft"
                  to={`/projects/${project.id}/plan-creation`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-bold text-slate-950">{project.product_name}</p>
                      <p className="mt-1 text-xs text-slate-500">
                        {project.product_category || "General"} / {compactId(project.id)}
                      </p>
                    </div>
                    <span className="text-xs text-slate-400">{formatDate(project.updated_at)}</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      </aside>
    </div>
  );
}
