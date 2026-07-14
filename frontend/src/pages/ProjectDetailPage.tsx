import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Link, useNavigate, useParams } from "react-router-dom";
import PlanCreationCard, { type PlanWorkflowStep } from "../components/PlanCreationCard";
import {
  deleteProject,
  generatePlanCreation,
  generateKeyframeSlotImage,
  generateReferenceAssetImage,
  generateSceneVideo,
  getProject,
  updateKeyframePromptSlot,
  updateReferenceAsset,
  updateSceneVideoPrompt,
  uploadKeyframeSlotImage,
  uploadProjectFiles,
  uploadReferenceAssetImage,
  uploadSceneVideo,
} from "../api/projects";
import { getApiErrorMessage, toApiUrl } from "../api/client";
import type { Project } from "../types";
import { compactId, formatDate } from "../utils/format";

type ActionName = "load" | "upload" | "planCreation" | "referenceAsset" | "keyframe" | "clip" | "delete";
type ProjectPhase = "brief" | "plan-creation";
type PlanMode = "manual" | "automation";
type ReferenceAssetType = "character" | "location";

interface ProjectDetailPageProps {
  phase: ProjectPhase;
}

const GOOGLE_FLOW_URL = "https://labs.google/fx/tools/flow/project/4c8abe81-9457-43d0-bafb-3d28c7757b3c";

export default function ProjectDetailPage({ phase }: ProjectDetailPageProps) {
  const { id } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState<Project | null>(null);
  const [loadingAction, setLoadingAction] = useState<ActionName | null>("load");
  const [error, setError] = useState<string | null>(null);
  const [planWorkflowStep, setPlanWorkflowStep] = useState<PlanWorkflowStep>("reference-assets");
  const [planMode, setPlanMode] = useState<PlanMode>("manual");
  const [headerSlot, setHeaderSlot] = useState<HTMLElement | null>(null);
  const [showRegenerateWarning, setShowRegenerateWarning] = useState(false);
  const productReferenceInputRef = useRef<HTMLInputElement>(null);

  const canAct = Boolean(project && !loadingAction);
  const projectBase = id ? `/projects/${id}` : "/projects";

  useEffect(() => {
    setHeaderSlot(document.getElementById("app-header-actions"));
  }, []);

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

  const runPlanCreation = async (onSuccess?: () => void) => {
    if (!id) {
      return;
    }
    setLoadingAction("planCreation");
    setError(null);
    try {
      await generatePlanCreation(id);
      await refreshProject();
      setPlanWorkflowStep("reference-assets");
      onSuccess?.();
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoadingAction(null);
    }
  };

  const handleUploadImageReferences = async (files: File[]) => {
    if (!id || files.length === 0) {
      return;
    }
    setLoadingAction("upload");
    setError(null);
    try {
      await uploadProjectFiles(id, files);
      await refreshProject();
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoadingAction(null);
    }
  };

  const handleUploadReferenceAsset = async (assetType: ReferenceAssetType, file: File) => {
    if (!id) {
      return;
    }
    setLoadingAction("upload");
    setError(null);
    try {
      await uploadReferenceAssetImage(id, assetType, file);
      await refreshProject();
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoadingAction(null);
    }
  };

  const handleGenerateReferenceAsset = async (assetType: ReferenceAssetType, imagePrompt: string) => {
    if (!id) {
      return;
    }
    setLoadingAction("referenceAsset");
    setError(null);
    try {
      await updateReferenceAsset(id, assetType, { imagePrompt });
      await generateReferenceAssetImage(id, assetType);
      await refreshProject();
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoadingAction(null);
    }
  };

  const handleGenerateKeyframe = async (sceneIndex: number, slotId: string, prompt: string) => {
    if (!id) {
      return;
    }
    setLoadingAction("keyframe");
    setError(null);
    try {
      await updateKeyframePromptSlot(id, sceneIndex, slotId, { prompt });
      await generateKeyframeSlotImage(id, sceneIndex, slotId);
      await refreshProject();
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoadingAction(null);
    }
  };

  const handleUploadKeyframe = async (sceneIndex: number, slotId: string, file: File) => {
    if (!id) {
      return;
    }
    setLoadingAction("keyframe");
    setError(null);
    try {
      await uploadKeyframeSlotImage(id, sceneIndex, slotId, file);
      await refreshProject();
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoadingAction(null);
    }
  };

  const handleGenerateClip = async (sceneIndex: number, prompt: string) => {
    if (!id) {
      return;
    }
    setLoadingAction("clip");
    setError(null);
    try {
      await updateSceneVideoPrompt(id, sceneIndex, prompt);
      await generateSceneVideo(id, sceneIndex);
      await refreshProject();
    } catch (err) {
      setError(getApiErrorMessage(err));
      await refreshProject();
    } finally {
      setLoadingAction(null);
    }
  };

  const handleUploadClip = async (sceneIndex: number, file: File) => {
    if (!id) {
      return;
    }
    setLoadingAction("clip");
    setError(null);
    try {
      await uploadSceneVideo(id, sceneIndex, file);
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

  const handleRegeneratePlan = async () => {
    setShowRegenerateWarning(false);
    await runPlanCreation();
  };

  if (loadingAction === "load" && !project) {
    return <div className="card p-6 text-sm text-slate-500">Loading project...</div>;
  }

  const hasPlanCreation = Boolean(project?.creative_plan);
  const workflowItems: Array<{ id: PlanWorkflowStep; label: string; description: string }> = [
    { id: "reference-assets", label: "Character + location refs", description: "Create or upload two base images" },
    { id: "keyframes", label: "Scene keyframes", description: "Create keyframe refs per 4s scene" },
    { id: "scene-clips", label: "4s clip prompts", description: "Generate one clip per scene" },
  ];
  const currentWorkflowIndex = Math.max(
    0,
    workflowItems.findIndex((item) => item.id === planWorkflowStep),
  );
  const workflowState = (index: number): "current" | "complete" | "ready" => {
    if (index === currentWorkflowIndex) {
      return "current";
    }
    if (index < currentWorkflowIndex) {
      return "complete";
    }
    return "ready";
  };
  const previousWorkflowStep = workflowItems[currentWorkflowIndex - 1]?.id;
  const nextWorkflowStep = workflowItems[currentWorkflowIndex + 1]?.id;
  const activeWorkflowItem = workflowItems[currentWorkflowIndex] ?? workflowItems[0];
  const completedWorkflowCount = Math.max(0, currentWorkflowIndex);
  const planHeaderPortal =
    phase === "plan-creation" && headerSlot
      ? createPortal(
          <div className="hidden min-w-0 items-center justify-end gap-4 xl:flex">
            <div className="min-w-[260px] max-w-[340px]">
              <div className="flex items-center justify-between gap-3">
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-teal-700">Plan Creation</p>
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                  Step {currentWorkflowIndex + 1}/{workflowItems.length}
                </span>
              </div>
              <p className="mt-1 truncate text-sm font-semibold text-slate-950">{activeWorkflowItem.label}</p>
              <div className="mt-2 h-1 rounded-full bg-slate-100">
                <div
                  className="h-1 rounded-full bg-teal-500 transition-all"
                  style={{ width: `${((currentWorkflowIndex + 1) / workflowItems.length) * 100}%` }}
                />
              </div>
            </div>

            <div className="grid w-56 grid-cols-2 rounded-xl border border-slate-200 bg-slate-100 p-1">
              <button
                className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
                  planMode === "manual" ? "bg-slate-950 text-white shadow-sm" : "text-slate-600 hover:text-slate-950"
                }`}
                onClick={() => setPlanMode("manual")}
                type="button"
              >
                Manual
              </button>
              <button
                className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
                  planMode === "automation" ? "bg-slate-950 text-white shadow-sm" : "text-slate-600 hover:text-slate-950"
                }`}
                onClick={() => setPlanMode("automation")}
                type="button"
              >
                Automation
              </button>
            </div>

          </div>,
          headerSlot,
        )
      : null;

  return (
    <div className="space-y-6">
      {planHeaderPortal}
      {showRegenerateWarning ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/55 px-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-rose-600">Reset warning</p>
            <h3 className="mt-2 text-xl font-semibold text-slate-950">Regenerate Plan Creation?</h3>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              This will rebuild the plan from the brief and reset the workflow to the first step. Product images from the brief stay, but character,
              location, keyframe, and clip reference images from later phases will be removed from this project.
            </p>
            <div className="mt-6 flex flex-wrap justify-end gap-3">
              <button className="btn-secondary" type="button" onClick={() => setShowRegenerateWarning(false)}>
                Cancel
              </button>
              <button className="btn-danger" disabled={!canAct} type="button" onClick={() => void handleRegeneratePlan()}>
                {loadingAction === "planCreation" ? "Regenerating..." : "Regenerate from start"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
      {phase === "brief" ? (
      <div className="rounded-2xl border border-slate-200 bg-slate-950 p-5 text-white shadow-soft">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-3xl font-semibold">{project?.product_name ?? "Project"}</h2>
            {project ? (
              <p className="mt-2 text-sm text-slate-300">
                {project.product_category || "General product"} / {compactId(project.id)} / Updated {formatDate(project.updated_at)}
              </p>
            ) : null}
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              className="rounded-md border border-white/20 bg-white/10 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/15"
              disabled={!project || Boolean(loadingAction)}
              onClick={() => void handleRefresh()}
              type="button"
            >
              Refresh Project
            </button>
            <button
              className="rounded-md border border-rose-300/40 bg-rose-500/10 px-4 py-2 text-sm font-semibold text-rose-100 transition hover:bg-rose-500/20"
              disabled={!project || Boolean(loadingAction)}
              onClick={handleDelete}
              type="button"
            >
              {loadingAction === "delete" ? "Deleting..." : "Delete"}
            </button>
          </div>
        </div>
      </div>
      ) : null}

      {error ? <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</div> : null}

      {project && phase === "brief" ? (
        <section className="card-accent overflow-hidden">
          <div className="border-b border-slate-200/80 px-6 py-5">
            <p className="text-xs font-bold uppercase tracking-wide text-teal-700">Input package</p>
            <h3 className="section-heading">Brief Input</h3>
            <p className="section-subtitle">Confirm the brief, upload product images, then generate a 4-second scene plan.</p>
          </div>
          <div className="space-y-7 px-6 py-6">
            <div>
              <h4 className="mt-1 text-lg font-semibold text-slate-950">Confirm brief input</h4>
              <p className="mt-1 text-sm text-slate-500">This is the text context Gemini uses together with the product reference images.</p>
            </div>
            <div className="grid gap-7 lg:grid-cols-2">
              <div className="space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p className="field-label">Product description</p>
                <p className="text-sm leading-7 text-slate-700">{project.product_description || "Not specified"}</p>
                {project.audience ? (
                  <p className="text-sm leading-7 text-slate-700">
                    <span className="font-semibold text-slate-900">Audience:</span> {project.audience}
                  </p>
                ) : null}
              </div>
              <div className="space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p className="field-label">Brief</p>
                <p className="whitespace-pre-wrap text-sm leading-7 text-slate-700">{project.brief || "Not specified"}</p>
              </div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-teal-700">Product images</p>
                  <h4 className="mt-1 text-lg font-semibold text-slate-950">Upload product references</h4>
                  <p className="mt-1 text-sm leading-6 text-slate-500">
                    Upload app screenshots, product photos, logo, packaging, or UI screens here before Plan Creation. Next step: Gemini splits the brief into 4-second scene clips.
                  </p>
                </div>
                <button className="btn-primary" disabled={!canAct} type="button" onClick={() => productReferenceInputRef.current?.click()}>
                  {loadingAction === "upload" ? "Uploading..." : "Upload Product Images"}
                </button>
                <input
                  ref={productReferenceInputRef}
                  className="hidden"
                  type="file"
                  multiple
                  accept="image/*,.pdf,.txt,.json"
                  onChange={(event) => {
                    const files = Array.from(event.target.files ?? []);
                    event.currentTarget.value = "";
                    void handleUploadImageReferences(files);
                  }}
                />
              </div>

              {project.uploaded_files.length ? (
                <div className="mt-5 border-t border-slate-200 pt-5">
                  <p className="field-label">Uploaded product references</p>
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
                </div>
              ) : (
                <p className="mt-4 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                  You can generate text-only, but product screenshots or photos make the scene prompts more usable.
                </p>
              )}
            </div>
          </div>
          <div className="border-t border-slate-200 px-6 py-5">
            <div className="flex justify-end">
              <button
                className="btn-primary"
                disabled={!canAct}
                onClick={() => void runPlanCreation(() => navigate(`${projectBase}/plan-creation`))}
                type="button"
              >
                {loadingAction === "planCreation" ? "Generating Plan Creation..." : hasPlanCreation ? "Regenerate 4s Plan Creation" : "Generate 4s Plan Creation"}
              </button>
            </div>
          </div>
        </section>
      ) : null}

      {phase === "plan-creation" ? (
        <section className="overflow-hidden border-t border-slate-200 bg-white">
          <div className="grid min-h-[calc(100vh-88px)] lg:grid-cols-[280px_minmax(0,1fr)] 2xl:grid-cols-[300px_minmax(0,1fr)]">
            <aside className="border-r border-slate-800 bg-slate-950 px-5 py-6 text-white">
              <div className="sticky top-6 space-y-5">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-teal-300">Project</p>
                  <h2 className="mt-2 text-[22px] font-semibold leading-tight">{project?.product_name ?? "Project"}</h2>
                  {project ? (
                    <p className="mt-2 text-sm leading-6 text-slate-400">
                      {project.product_category || "General product"} / {compactId(project.id)}
                      <br />
                      Updated {formatDate(project.updated_at)}
                    </p>
                  ) : null}
                  <div className="mt-5 grid grid-cols-2 gap-2">
                    <button
                      className="rounded-lg border border-amber-300/30 bg-amber-400/10 px-3 py-2 text-sm font-semibold text-amber-50 transition hover:bg-amber-400/20"
                      disabled={!project || Boolean(loadingAction)}
                      onClick={() => setShowRegenerateWarning(true)}
                      type="button"
                    >
                      {loadingAction === "planCreation" ? "Running..." : "Regenerate"}
                    </button>
                    <button
                      className="rounded-lg border border-rose-300/25 bg-rose-500/10 px-3 py-2 text-sm font-semibold text-rose-100 transition hover:bg-rose-500/20"
                      disabled={!project || Boolean(loadingAction)}
                      onClick={handleDelete}
                      type="button"
                    >
                      {loadingAction === "delete" ? "Deleting..." : "Delete"}
                    </button>
                  </div>
                </div>

                <nav className="space-y-2.5">
                  {workflowItems.map((item, index) => {
                    const state = workflowState(index);
                    return (
                      <button
                        key={item.id}
                        className={`w-full rounded-2xl border px-4 py-4 text-left transition ${
                          state === "current"
                            ? "border-rose-300/50 bg-rose-500/15"
                            : state === "complete"
                              ? "border-emerald-300/40 bg-emerald-500/10"
                              : "border-white/10 bg-white/[0.04] hover:border-teal-300/50 hover:bg-white/[0.07]"
                        }`}
                        onClick={() => setPlanWorkflowStep(item.id)}
                        type="button"
                      >
                        <div className="flex items-start gap-3">
                          <span
                            className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-sm font-semibold ${
                              state === "current" ? "bg-rose-500 text-white" : state === "complete" ? "bg-emerald-500 text-white" : "bg-white/10 text-slate-300"
                            }`}
                          >
                            {index + 1}
                          </span>
                          <span>
                            <span className={`block text-[11px] font-semibold uppercase tracking-[0.14em] ${state === "current" ? "text-rose-200" : state === "complete" ? "text-emerald-200" : "text-slate-500"}`}>
                              {state === "current" ? "In progress" : state === "complete" ? "Complete" : "Ready"}
                            </span>
                            <span className="mt-1 block text-sm font-semibold text-white">{item.label}</span>
                            <span className="mt-1 block text-xs leading-5 text-slate-400">{item.description}</span>
                          </span>
                        </div>
                      </button>
                    );
                  })}
                </nav>

              </div>
            </aside>

            <div className="min-w-0 bg-[#f6f8fb]">
              <main className="p-7 xl:p-10">
                {project?.creative_plan ? (
                  <>
                    {planWorkflowStep === "keyframes" && project.uploaded_files.length ? (
                      <div className="mb-6 rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
                        <p className="field-label">Uploaded reference images</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {project.uploaded_files.map((file) => (
                            <a
                              key={file.id}
                              className="inline-flex max-w-full items-center rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-700 transition hover:border-teal-300 hover:bg-teal-50 hover:text-teal-800"
                              href={toApiUrl(file.url)}
                              target="_blank"
                              rel="noreferrer"
                            >
                              {file.file_name}
                            </a>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    <PlanCreationCard
                      googleFlowUrl={GOOGLE_FLOW_URL}
                      isGeneratingClip={loadingAction === "clip"}
                      isGeneratingKeyframe={loadingAction === "keyframe"}
                      isGeneratingReferenceAsset={loadingAction === "referenceAsset"}
                      isUploadingClip={loadingAction === "clip"}
                      isUploadingKeyframe={loadingAction === "keyframe"}
                      isUploadingReferenceAsset={loadingAction === "upload"}
                      mode={planMode}
                      onGenerateClip={(sceneIndex, prompt) => void handleGenerateClip(sceneIndex, prompt)}
                      onGenerateKeyframe={(sceneIndex, slotId, prompt) => void handleGenerateKeyframe(sceneIndex, slotId, prompt)}
                      onGenerateReferenceAsset={(assetType, imagePrompt) => void handleGenerateReferenceAsset(assetType, imagePrompt)}
                      onUploadClip={(sceneIndex, file) => void handleUploadClip(sceneIndex, file)}
                      onUploadKeyframe={(sceneIndex, slotId, file) => void handleUploadKeyframe(sceneIndex, slotId, file)}
                      onUploadReferenceAsset={(assetType, file) => void handleUploadReferenceAsset(assetType, file)}
                      planCreation={project.creative_plan}
                      step={planWorkflowStep}
                      uploadedFiles={project.uploaded_files}
                    />

                    <div className="mt-8 flex items-center justify-between border-t border-slate-200 pt-5">
                      <button
                        className="btn-secondary"
                        disabled={!previousWorkflowStep}
                        type="button"
                        onClick={() => previousWorkflowStep && setPlanWorkflowStep(previousWorkflowStep)}
                      >
                        Back
                      </button>
                      <div className="text-sm font-bold text-slate-500">
                        {completedWorkflowCount} / {workflowItems.length} complete
                      </div>
                      {nextWorkflowStep ? (
                        <button className="btn-primary" type="button" onClick={() => setPlanWorkflowStep(nextWorkflowStep)}>
                          Next
                        </button>
                      ) : (
                        <Link className="btn-secondary" to={`${projectBase}/brief`}>
                          Back to brief
                        </Link>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center shadow-sm">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-teal-700">Ready to generate</p>
                    <h4 className="mt-2 text-2xl font-semibold text-slate-950">No Plan Creation yet</h4>
                    <p className="mx-auto mt-3 max-w-2xl text-sm leading-6 text-slate-600">
                      Generate the plan first. The dashboard will then walk through character/location references, scene keyframes, and 4-second clip prompts.
                    </p>
                    <div className="mt-6 flex flex-wrap justify-center gap-3">
                      <Link className="btn-secondary" to={`${projectBase}/brief`}>
                        Review brief
                      </Link>
                      <button className="btn-primary" disabled={!canAct} onClick={() => void runPlanCreation()} type="button">
                        {loadingAction === "planCreation" ? "Generating..." : "Generate Plan"}
                      </button>
                    </div>
                  </div>
                )}
              </main>
            </div>
          </div>
        </section>
      ) : null}
    </div>
  );
}
