import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import CreativeAngleCard from "../components/CreativeAngleCard";
import ProductBriefCard from "../components/ProductBriefCard";
import ProductIntelligenceCard from "../components/ProductIntelligenceCard";
import ProgressSteps from "../components/ProgressSteps";
import VariantCard from "../components/VariantCard";
import {
  analyzeProject,
  deleteProject,
  exportProductionPackage,
  generateAngles,
  generateVariants,
  getProject,
  renderProject,
} from "../api/projects";
import { getApiErrorMessage, toApiUrl } from "../api/client";
import type { Project } from "../types";
import { compactId, formatDate, formatList } from "../utils/format";

type ActionName = "load" | "analyze" | "angles" | "variants" | "export" | "render" | "delete";
type ProjectPhase = "assets" | "intelligence" | "angles" | "variants";

interface ProjectDetailPageProps {
  phase: ProjectPhase;
}

const phaseItems: Array<{ id: ProjectPhase; label: string; description: string }> = [
  { id: "assets", label: "Assets", description: "Inputs and files" },
  { id: "intelligence", label: "Intelligence", description: "Product brief" },
  { id: "angles", label: "Angles", description: "Creative strategy" },
  { id: "variants", label: "Variants", description: "Scripts and prompts" },
];

export default function ProjectDetailPage({ phase }: ProjectDetailPageProps) {
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

  const runAction = async (
    action: Exclude<ActionName, "load" | "delete">,
    task: () => Promise<unknown>,
    onSuccess?: () => void,
  ) => {
    if (!id) {
      return;
    }
    setLoadingAction(action);
    setError(null);
    try {
      await task();
      await refreshProject();
      onSuccess?.();
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

  const projectBase = id ? `/projects/${id}` : "/projects";

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-slate-200 bg-slate-950 p-5 text-white shadow-soft">
        <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-3xl font-black">{project?.product_name ?? "Project"}</h2>
          {project ? (
            <p className="mt-2 text-sm text-slate-300">
              {project.product_category || "General product"} / {compactId(project.id)} / Updated {formatDate(project.updated_at)}
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="rounded-md border border-white/20 bg-white/10 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/15" disabled={!project || Boolean(loadingAction)} onClick={() => void handleRefresh()} type="button">
            Refresh Project
          </button>
          <button className="rounded-md border border-rose-300/40 bg-rose-500/10 px-4 py-2 text-sm font-semibold text-rose-100 transition hover:bg-rose-500/20" disabled={!project || Boolean(loadingAction)} onClick={handleDelete} type="button">
            {loadingAction === "delete" ? "Deleting..." : "Delete"}
          </button>
        </div>
        </div>
      </div>

      {error ? <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</div> : null}

      <ProgressSteps project={project} />

      <nav className="card-accent p-4">
        <div className="grid gap-3 md:grid-cols-4">
          {phaseItems.map((item, index) => (
            <Link
              key={item.id}
              className={`rounded-lg border p-4 transition hover:-translate-y-0.5 hover:shadow-soft ${
                phase === item.id ? "border-teal-300 bg-teal-50" : "border-slate-200 bg-white"
              }`}
              to={`${projectBase}/${item.id}`}
            >
              <span className={`flex h-8 w-8 items-center justify-center rounded-md text-xs font-black ${phase === item.id ? "bg-teal-600 text-white" : "bg-slate-100 text-slate-500"}`}>
                {index + 1}
              </span>
              <p className="mt-3 text-sm font-black text-slate-950">{item.label}</p>
              <p className="mt-1 text-xs text-slate-500">{item.description}</p>
            </Link>
          ))}
        </div>
      </nav>

      {project && phase === "assets" ? (
        <section className="card-accent p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-wide text-teal-700">Input package</p>
              <h3 className="section-heading">Project Assets</h3>
              <p className="section-subtitle">Uploaded file preview names and project inputs.</p>
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="metric-tile">
              <p className="field-label">Description</p>
              <p className="mt-1 text-sm text-slate-700">{project.product_description || "Not specified"}</p>
            </div>
            <div className="metric-tile">
              <p className="field-label">Setup</p>
              <p className="mt-1 text-sm text-slate-700">
                {project.goal} / {project.platform} / {project.duration}
              </p>
            </div>
            <div className="metric-tile">
              <p className="field-label">Brand colors</p>
              <p className="mt-1 text-sm text-slate-700">{formatList(project.brand_colors)}</p>
            </div>
            <div className="metric-tile">
              <p className="field-label">Claims to avoid</p>
              <p className="mt-1 text-sm text-slate-700">{formatList(project.claims_to_avoid)}</p>
            </div>
            <div className="metric-tile md:col-span-2">
              <p className="field-label">Uploaded files</p>
              {project.uploaded_files.length ? (
                <div className="mt-2 grid gap-2 sm:grid-cols-2">
                  {project.uploaded_files.map((file) => (
                    <a key={file.id} className="block truncate rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-800 hover:border-teal-300 hover:text-teal-800" href={toApiUrl(file.url)} target="_blank" rel="noreferrer">
                      {file.file_name}
                    </a>
                  ))}
                </div>
              ) : (
                <p className="mt-1 text-sm text-slate-500">No files uploaded.</p>
              )}
            </div>
          </div>
          <div className="mt-5 flex justify-end">
            <Link className="btn-primary" to={`${projectBase}/intelligence`}>
              Continue to Intelligence
            </Link>
          </div>
        </section>
      ) : null}

      {phase === "intelligence" ? (
      <section className="card-accent p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="inline-flex rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-xs font-black uppercase tracking-wide text-amber-800">
              Phase 1 / Product Intelligence
            </p>
            <h3 className="section-heading">Product Intelligence</h3>
            <p className="section-subtitle">Analyze product type, use case, audiences, proof points, and playbooks.</p>
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
        <ProductIntelligenceCard intelligence={project?.product_intelligence} />
        {project?.product_intelligence ? (
          <div className="mt-5 flex justify-end">
            <Link className="btn-primary" to={`${projectBase}/angles`}>
              Continue to Angles
            </Link>
          </div>
        ) : null}
      </section>
      ) : null}

      {phase === "intelligence" ? (
      <section className="card p-5">
        <div className="mb-4">
          <h3 className="section-heading">Legacy Product Brief</h3>
          <p className="section-subtitle">Compatibility output used by the existing creative flow.</p>
        </div>
        <ProductBriefCard brief={project?.product_brief} />
      </section>
      ) : null}

      {phase === "angles" ? (
      <section className="space-y-4">
        <div className="card-accent grid gap-4 p-5 md:grid-cols-[minmax(0,1fr)_auto] md:items-center">
          <div className="max-w-xl">
            <p className="inline-flex rounded-md border border-rose-200 bg-rose-50 px-2 py-1 text-xs font-black uppercase tracking-wide text-rose-800">
              Phase 2 / Creative Angles
            </p>
            <h3 className="section-heading">Creative Angles</h3>
            <p className="section-subtitle">Select one or two cards, or let backend pick top scoring angles.</p>
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
                void runAction(
                  "variants",
                  () => generateVariants(id as string, selectedAngles.length ? selectedAngles : undefined),
                  () => navigate(`${projectBase}/variants`),
                )
              }
              type="button"
            >
              {loadingAction === "variants" ? "Generating..." : "Generate 2 Variants"}
            </button>
            {project?.variants.length ? (
              <Link className="btn-secondary" to={`${projectBase}/variants`}>
                Continue to Variants
              </Link>
            ) : null}
          </div>
        </div>

        {project?.creative_angles.length ? (
          <div className="grid gap-4 xl:grid-cols-2">
            {project.creative_angles.map((angle) => (
              <CreativeAngleCard key={angle.id} angle={angle} selected={selectedAngles.includes(angle.id)} onToggle={toggleAngle} />
            ))}
          </div>
        ) : (
          <div className="empty-state">
            Creative angles will appear here after generation.
          </div>
        )}
      </section>
      ) : null}

      {phase === "variants" ? (
      <section className="space-y-4">
        <div className="card-accent p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-wide text-indigo-700">Phase 3</p>
              <h3 className="section-heading">Video Production Packages</h3>
              <p className="section-subtitle">Review scripts, character plans, reference prompts, production scenes, overlays, and export package files.</p>
            </div>
          </div>
        </div>

        {project?.variants.length ? (
          <div className="space-y-4">
            {project.variants.map((variant) => (
              <VariantCard
                key={variant.id}
                variant={variant}
                onExport={() => runAction("export", () => exportProductionPackage(id as string))}
                onRender={() => runAction("render", () => renderProject(id as string))}
                exporting={loadingAction === "export"}
                rendering={loadingAction === "render"}
                disabled={!canAct}
              />
            ))}
          </div>
        ) : (
          <div className="empty-state">
            Variants will appear after generation.
          </div>
        )}
      </section>
      ) : null}

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
