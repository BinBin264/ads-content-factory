import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import CreativeAngleCard from "../components/CreativeAngleCard";
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
  runPipelineStep,
  runVariantPipeline,
  uploadPipelineStepResult,
} from "../api/projects";
import { getApiErrorMessage, toApiUrl } from "../api/client";
import type { Project } from "../types";
import { compactId, formatDate, formatList } from "../utils/format";

type ActionName = "load" | "analyze" | "angles" | "variants" | "export" | "render" | "runPipeline" | "runStep" | "uploadStep" | "delete";
type ProjectPhase = "assets" | "intelligence" | "angles" | "variants";

interface ProjectDetailPageProps {
  phase: ProjectPhase;
}

const phaseItems: Array<{ id: ProjectPhase; label: string; description: string }> = [
  { id: "assets", label: "Assets", description: "Inputs and files" },
  { id: "intelligence", label: "Intelligence", description: "Product signals" },
  { id: "angles", label: "Angles", description: "Ad strategy" },
  { id: "variants", label: "Video Workflow", description: "Manual production" },
];

export default function ProjectDetailPage({ phase }: ProjectDetailPageProps) {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [project, setProject] = useState<Project | null>(null);
  const [selectedAngles, setSelectedAngles] = useState<string[]>([]);
  const [loadingAction, setLoadingAction] = useState<ActionName | null>("load");
  const [error, setError] = useState<string | null>(null);

  const canAct = Boolean(project && !loadingAction);
  const selectedAngleIdsFromQuery = useMemo(() => {
    const rawValue = new URLSearchParams(location.search).get("angle_ids");
    return rawValue ? rawValue.split(",").map((item) => item.trim()).filter(Boolean) : [];
  }, [location.search]);

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
  const hasIntelligence = Boolean(project?.product_intelligence);
  const hasAngles = Boolean(project?.creative_angles.length);
  const hasVideoWorkflow = Boolean(project?.variants.some((variant) => variant.production_package));
  const selectedAngleQuery = selectedAngles.length ? `?angle_ids=${selectedAngles.join(",")}` : "";
  const variantsPath = `${projectBase}/variants${selectedAngleQuery}`;
  const variantGenerationAngleIds = selectedAngleIdsFromQuery.length ? selectedAngleIdsFromQuery : undefined;
  const variantGenerationAngleNames =
    project?.creative_angles
      .filter((angle) => selectedAngleIdsFromQuery.includes(angle.id))
      .map((angle) => angle.name) ?? [];
  const phaseState = (item: ProjectPhase): "current" | "complete" | "ready" | "locked" => {
    if (item === phase) {
      return "current";
    }
    if (item === "assets") {
      return "complete";
    }
    if (item === "intelligence") {
      return hasIntelligence ? "complete" : "ready";
    }
    if (item === "angles") {
      if (hasAngles) {
        return "complete";
      }
      return hasIntelligence ? "ready" : "locked";
    }
    if (hasVideoWorkflow) {
      return "complete";
    }
    return hasAngles ? "ready" : "locked";
  };
  const phaseClass = (state: ReturnType<typeof phaseState>) => {
    if (state === "current") {
      return "border-rose-300 bg-rose-50";
    }
    if (state === "complete") {
      return "border-emerald-200 bg-emerald-50";
    }
    if (state === "ready") {
      return "border-slate-200 bg-white hover:-translate-y-0.5 hover:shadow-soft";
    }
    return "cursor-not-allowed border-slate-200 bg-slate-50 opacity-60";
  };
  const phaseBadgeClass = (state: ReturnType<typeof phaseState>) => {
    if (state === "current") {
      return "bg-rose-600 text-white";
    }
    if (state === "complete") {
      return "bg-emerald-600 text-white";
    }
    return "bg-slate-100 text-slate-500";
  };
  const phaseStatusLabel = (state: ReturnType<typeof phaseState>) => {
    if (state === "current") {
      return "In progress";
    }
    if (state === "complete") {
      return "Complete";
    }
    if (state === "ready") {
      return "Ready";
    }
    return "Locked";
  };

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
          {phaseItems.map((item, index) => {
            const state = phaseState(item.id);
            const content = (
              <>
                <div className="flex items-center justify-between gap-2">
                  <span className={`flex h-8 w-8 items-center justify-center rounded-md text-xs font-black ${phaseBadgeClass(state)}`}>
                    {index + 1}
                  </span>
                  <span className="text-xs font-bold uppercase tracking-wide text-slate-400">{phaseStatusLabel(state)}</span>
                </div>
                <p className="mt-3 text-sm font-black text-slate-950">{item.label}</p>
                <p className="mt-1 text-xs text-slate-500">{item.description}</p>
              </>
            );

            if (state === "locked") {
              return (
                <div key={item.id} className={`rounded-lg border p-4 transition ${phaseClass(state)}`}>
                  {content}
                </div>
              );
            }

            return (
              <Link key={item.id} className={`rounded-lg border p-4 transition ${phaseClass(state)}`} to={`${projectBase}/${item.id}`}>
                {content}
              </Link>
            );
          })}
        </div>
      </nav>

      {project && phase === "assets" ? (
        <section className="card-accent overflow-hidden">
          <div className="border-b border-slate-200/80 px-6 py-5">
            <div>
              <p className="text-xs font-bold uppercase tracking-wide text-teal-700">Input package</p>
              <h3 className="section-heading">Project Assets</h3>
              <p className="section-subtitle">Uploaded file preview names and project inputs.</p>
            </div>
          </div>
          <div className="space-y-7 px-6 py-6">
            <div className="grid gap-7 lg:grid-cols-[minmax(0,1.4fr)_minmax(280px,0.6fr)]">
              <div className="space-y-3">
                <p className="field-label">Description</p>
                <p className="max-w-3xl text-sm leading-7 text-slate-700">{project.product_description || "Not specified"}</p>
                {project.audience ? (
                  <p className="max-w-3xl text-sm leading-7 text-slate-700">
                    <span className="font-semibold text-slate-900">Audience:</span> {project.audience}
                  </p>
                ) : null}
              </div>
              <div>
                <p className="field-label">Setup</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {[project.goal, project.platform, project.duration].map((item) => (
                    <span key={item} className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700">
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div className="border-t border-slate-200 pt-6">
              <p className="field-label">Claims to avoid</p>
              <p className="mt-2 max-w-3xl text-sm leading-7 text-slate-700">{formatList(project.claims_to_avoid)}</p>
            </div>

            <div className="border-t border-slate-200 pt-6">
              <p className="field-label">Uploaded files</p>
              {project.uploaded_files.length ? (
                <div className="mt-3 flex flex-wrap gap-3">
                  {project.uploaded_files.map((file) => (
                    <a
                      key={file.id}
                      className="inline-flex max-w-full items-center rounded-md border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-semibold text-slate-800 transition hover:border-teal-300 hover:bg-teal-50 hover:text-teal-800"
                      href={toApiUrl(file.url)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {file.file_name}
                    </a>
                  ))}
                </div>
              ) : (
                <p className="mt-1 text-sm text-slate-500">No files uploaded.</p>
              )}
            </div>
          </div>
          <div className="border-t border-slate-200 px-6 py-5">
            <div className="flex justify-end">
            <Link className="btn-primary" to={`${projectBase}/intelligence`}>
              Next: Product Intelligence
            </Link>
            </div>
          </div>
        </section>
      ) : null}

      {phase === "intelligence" ? (
      <section className="card-accent p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="section-heading">Product Intelligence</h3>
            <p className="section-subtitle">Analyze product type, use case, audiences, proof points, and playbooks.</p>
          </div>
          <button
            className="btn-primary"
            disabled={!canAct}
            onClick={() => void runAction("analyze", () => analyzeProject(id as string))}
            type="button"
          >
            {loadingAction === "analyze" ? "Analyzing..." : hasIntelligence ? "Re-analyze Product" : "Analyze Product"}
          </button>
        </div>
        <ProductIntelligenceCard intelligence={project?.product_intelligence} />
        {project?.product_intelligence ? (
          <div className="mt-5 flex justify-end">
            <Link className="btn-primary" to={`${projectBase}/angles`}>
              Next: Creative Angles
            </Link>
          </div>
        ) : null}
      </section>
      ) : null}

      {phase === "angles" ? (
      <section className="space-y-4">
        <div className="card-accent overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 px-5 py-4">
            <div>
              <h3 className="section-heading">Creative Angles</h3>
              <p className="section-subtitle">Generate strategy cards, then select up to two for variant production.</p>
            </div>
            <button
              className="btn-secondary"
              disabled={!canAct || !hasIntelligence}
              onClick={() => void runAction("angles", () => generateAngles(id as string))}
              type="button"
            >
              {loadingAction === "angles" ? "Generating..." : hasAngles ? "Regenerate Angles" : "Generate Angles"}
            </button>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
            <p className="text-sm text-slate-600">
              {!hasIntelligence
                ? "Analyze Product first so angles can use product signals instead of generic guesses."
                : project?.creative_angles.length
                ? selectedAngles.length
                  ? `${selectedAngles.length} angle selected. Next step will generate video workflows from this selection.`
                  : "No angle selected. The next step can auto-pick the top scoring angles."
                : "Generate angles before moving to variant production."}
            </p>
            {project?.creative_angles.length ? (
              <Link className="btn-primary" to={variantsPath}>
                Next: Video Workflow
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
              <h3 className="section-heading">Video Production Packages</h3>
              <p className="section-subtitle">Generate a practical step-by-step workflow for manual video production: character refs, keyframes, scene animation, overlays, edit, and export.</p>
              {project?.creative_angles.length ? (
                <p className="mt-2 text-sm text-slate-600">
                  {variantGenerationAngleNames.length
                    ? `Using selected angles: ${variantGenerationAngleNames.join(", ")}.`
                    : "No angle passed from the Angles tab. Backend will use top scoring angles."}
                </p>
              ) : null}
            </div>
            <button
              className="btn-primary"
              disabled={!canAct || !project?.creative_angles.length}
              onClick={() =>
                void runAction("variants", () => generateVariants(id as string, variantGenerationAngleIds))
              }
              type="button"
            >
              {loadingAction === "variants" ? "Generating..." : hasVideoWorkflow ? "Regenerate Video Workflow" : "Generate Video Workflow"}
            </button>
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
                onRunPipeline={() => runAction("runPipeline", () => runVariantPipeline(id as string, variant.id))}
                onRunStep={(stepId) => runAction("runStep", () => runPipelineStep(id as string, variant.id, stepId))}
                onUploadStepResult={(stepId, file, assetKey) => runAction("uploadStep", () => uploadPipelineStepResult(id as string, variant.id, stepId, file, assetKey))}
                exporting={loadingAction === "export"}
                rendering={loadingAction === "render"}
                runningPipeline={loadingAction === "runPipeline"}
                runningStep={loadingAction === "runStep"}
                uploadingStep={loadingAction === "uploadStep"}
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
    </div>
  );
}
