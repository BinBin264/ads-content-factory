import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import ProjectForm from "../components/ProjectForm";
import SampleInputsPanel from "../components/SampleInputsPanel";
import { createProject, listProjects } from "../api/projects";
import { getApiErrorMessage } from "../api/client";
import type { CreateProjectValues, Project } from "../types";
import { compactId, formatDate } from "../utils/format";

export default function HomePage() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sampleValues, setSampleValues] = useState<CreateProjectValues | null>(null);

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
      navigate(`/projects/${project.id}`);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
      <ProjectForm loading={loading} sampleValues={sampleValues} onSubmit={handleCreateProject} />

      <aside className="space-y-4">
        {error ? <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</div> : null}
        <SampleInputsPanel onSelect={setSampleValues} />
        <section className="card p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-950">Projects</h2>
              <p className="text-sm text-slate-500">Recent local MVP projects.</p>
            </div>
            <button className="btn-secondary px-3 py-1 text-xs" type="button" onClick={() => void loadProjects()}>
              Refresh
            </button>
          </div>

          {projects.length === 0 ? (
            <p className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-500">No projects yet.</p>
          ) : (
            <div className="space-y-3">
              {projects.map((project) => (
                <Link
                  key={project.id}
                  className="block rounded-lg border border-slate-200 bg-white p-4 transition hover:border-slate-400"
                  to={`/projects/${project.id}`}
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
