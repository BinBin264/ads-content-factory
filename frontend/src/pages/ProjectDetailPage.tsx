import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import CreativeAngleCard from "../components/CreativeAngleCard";
import ProductBriefCard from "../components/ProductBriefCard";
import ProgressSteps from "../components/ProgressSteps";
import VariantCard from "../components/VariantCard";
import {
  analyzeProject,
  deleteProject,
  generateAngles,
  generateVariants,
  getProject,
  mockRender,
} from "../api/projects";
import { getApiErrorMessage, toApiUrl } from "../api/client";
import type { Project } from "../types";
import { compactId, formatDate } from "../utils/format";

type ActionName = "load" | "analyze" | "angles" | "variants" | "render" | "delete";

export default function ProjectDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState<Project | null>(null);
  const [selectedAngles, setSelectedAngles] = useState<string[]>([]);
  const [loadingAction, setLoadingAction] = useState<ActionName | null>("load");
  const [error, setError] = useState<string | null>(null);
  const [showJson, setShowJson] = useState(false);

  const canAct = Boolean(project && !loadingAction);
  const jsonDebug = useMemo(() => JSON.stringify(project, null, 2), [project]);

  const refreshProject = async () => {
    if (!id) {
      return;
    }
    const nextProject = await getProject(id);
    setProject(nextProject);
  };

  useEffect(() => {
    const load = async () => {
      if (!id) {
        return;
      }
      setLoadingAction("load");
      setError(null);
      try {
        await refreshProject();
      } catch (err) {
        setError(getApiErrorMessage(err));
      } finally {
        setLoadingAction(null);
      }
    };
    void load();
  }, [id]);

  const runAction = async (action: Exclude<ActionName, "load" | "delete">, task: () => Promise<unknown>) => {
    if (!id) {
      return;
    }
    setLoadingAction(action);
    setError(null);
    try {
      await task();
      await refreshProject();
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoadingAction(null);
    }
  };

  const handleRefresh = async () => {
    setLoadingAction("load");
    setError(null);
    try {
      await refreshProject();
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoadingAction(null);
    }
  };

  const handleDelete = async () => {
    if (!id) {
      return;
    }
    setLoadingAction("delete");
    setError(null);
    try {
      await deleteProject(id);
      navigate("/");
    } catch (err) {
      setError(getApiErrorMessage(err));
      setLoadingAction(null);
    }
  };

  const toggleAngle = (angleId: string) => {
    setSelectedAngles((current) => {
      if (current.includes(angleId)) {
        return current.filter((idValue) => idValue !== angleId);
      }
      if (current.length >= 2) {
        return [current[1], angleId];
      }
      return [...current, angleId];
    });
  };

  if (loadingAction === "load" && !project) {
    return <div className="card p-6 text-sm text-slate-500">Loading project...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link className="text-sm font-semibold text-slate-500 hover:text-slate-900" to="/">
            Back to projects
          </Link>
          <h2 className="mt-2 text-2xl font-bold text-slate-950">{project?.product_name ?? "Project"}</h2>
          {project ? (
            <p className="mt-1 text-sm text-slate-500">
              {project.product_category || "General product"} · {compactId(project.id)} · Updated {formatDate(project.updated_at)}
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="btn-secondary" disabled={!project || Boolean(loadingAction)} onClick={() => void handleRefresh()} type="button">
            Refresh Project
          </button>
          <button className="btn-secondary border-red-200 text-red-700 hover:bg-red-50" disabled={!project || Boolean(loadingAction)} onClick={handleDelete} type="button">
            {loadingAction === "delete" ? "Deleting..." : "Delete"}
          </button>
        </div>
      </div>

      {error ? <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</div> : null}

      <ProgressSteps project={project} />

      {project ? (
        <section className="card p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-base font-bold text-slate-950">Project Assets</h3>
              <p className="text-sm text-slate-500">Uploaded file preview names and project inputs.</p>
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-lg bg-slate-50 p-4">
              <p className="field-label">Description</p>
              <p className="mt-1 text-sm text-slate-700">{project.product_description || "Not specified"}</p>
            </div>
            <div className="rounded-lg bg-slate-50 p-4">
              <p className="field-label">Audience</p>
              <p className="mt-1 text-sm text-slate-700">{project.audience || "Not specified"}</p>
            </div>
            <div className="rounded-lg bg-slate-50 p-4">
              <p className="field-label">Setup</p>
              <p className="mt-1 text-sm text-slate-700">
                {project.goal} · {project.platform} · {project.duration}
              </p>
            </div>
            <div className="rounded-lg bg-slate-50 p-4">
              <p className="field-label">Uploaded files</p>
              {project.uploaded_files.length ? (
                <div className="mt-2 space-y-2">
                  {project.uploaded_files.map((file) => (
                    <a key={file.id} className="block truncate text-sm font-semibold text-slate-800 hover:text-slate-950" href={toApiUrl(file.url)} target="_blank" rel="noreferrer">
                      {file.file_name}
                    </a>
                  ))}
                </div>
              ) : (
                <p className="mt-1 text-sm text-slate-500">No files uploaded.</p>
              )}
            </div>
          </div>
        </section>
      ) : null}

      <section className="card p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-bold text-slate-950">Product Intelligence</h3>
            <p className="text-sm text-slate-500">Analyze product positioning and proof points.</p>
          </div>
          <button
            className="btn-primary"
            disabled={!canAct}
            onClick={() => void runAction("analyze", () => analyzeProject(id as string))}
            type="button"
          >
            {loadingAction === "analyze" ? "Analyzing..." : "Analyze Product"}
          </button>
        </div>
        <ProductBriefCard brief={project?.product_brief} />
      </section>

      <section className="space-y-4">
        <div className="card flex flex-wrap items-center justify-between gap-3 p-5">
          <div>
            <h3 className="text-base font-bold text-slate-950">Creative Angles</h3>
            <p className="text-sm text-slate-500">Select two cards or let backend pick the top scoring angles.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              className="btn-secondary"
              disabled={!canAct}
              onClick={() => void runAction("angles", () => generateAngles(id as string))}
              type="button"
            >
              {loadingAction === "angles" ? "Generating..." : "Generate Angles"}
            </button>
            <button
              className="btn-primary"
              disabled={!canAct || !project?.creative_angles.length}
              onClick={() =>
                void runAction("variants", () => generateVariants(id as string, selectedAngles.length >= 2 ? selectedAngles : undefined))
              }
              type="button"
            >
              {loadingAction === "variants" ? "Generating..." : "Generate 2 Variants"}
            </button>
          </div>
        </div>

        {project?.creative_angles.length ? (
          <div className="grid gap-4 xl:grid-cols-2">
            {project.creative_angles.map((angle) => (
              <CreativeAngleCard key={angle.id} angle={angle} selected={selectedAngles.includes(angle.id)} onToggle={toggleAngle} />
            ))}
          </div>
        ) : (
          <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-500">
            Creative angles will appear here after generation.
          </div>
        )}
      </section>

      <section className="space-y-4">
        <div className="card p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-base font-bold text-slate-950">Variants Output</h3>
              <p className="text-sm text-slate-500">Review scripts, storyboards, prompts, captions, and exports.</p>
            </div>
            <button
              className="btn-primary"
              disabled={!canAct || !project?.variants.length}
              onClick={() => void runAction("render", () => mockRender(id as string))}
              type="button"
            >
              {loadingAction === "render" ? "Rendering..." : "Mock Render"}
            </button>
          </div>
        </div>

        {project?.variants.length ? (
          <div className="space-y-4">
            {project.variants.map((variant) => (
              <VariantCard key={variant.id} variant={variant} />
            ))}
          </div>
        ) : (
          <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-500">
            Variants will appear after generation.
          </div>
        )}
      </section>

      <section className="card p-5">
        <button className="flex w-full items-center justify-between text-left" type="button" onClick={() => setShowJson((current) => !current)}>
          <span>
            <span className="block text-base font-bold text-slate-950">Project JSON Debug</span>
            <span className="text-sm text-slate-500">Collapse or expand the raw API response.</span>
          </span>
          <span className="rounded-md bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600">{showJson ? "Hide" : "Show"}</span>
        </button>
        {showJson ? <pre className="mt-4 max-h-[520px] overflow-auto rounded-lg bg-slate-950 p-4 text-xs leading-5 text-slate-50">{jsonDebug}</pre> : null}
      </section>
    </div>
  );
}
