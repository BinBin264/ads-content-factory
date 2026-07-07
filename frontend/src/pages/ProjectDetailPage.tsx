import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import PlanCreationCard from "../components/PlanCreationCard";
import { deleteProject, generatePlanCreation, getProject, uploadProjectFiles } from "../api/projects";
import { getApiErrorMessage, toApiUrl } from "../api/client";
import type { Project, StorytellingScene } from "../types";
import { compactId, formatDate } from "../utils/format";

type ActionName = "load" | "upload" | "planCreation" | "delete";
type ProjectPhase = "brief" | "plan-creation";
type PlanPipelineStep = "scene-plan" | "image-references" | "scene-clips";

interface ProjectDetailPageProps {
  phase: ProjectPhase;
}

const phaseItems: Array<{ id: ProjectPhase; label: string; description: string }> = [
  { id: "brief", label: "Brief Input", description: "Project setup and uploaded references" },
  { id: "plan-creation", label: "Plan Creation", description: "4-second scene clips and copy-ready prompts" },
];

const GOOGLE_FLOW_URL = "https://labs.google/fx/tools/flow/project/4c8abe81-9457-43d0-bafb-3d28c7757b3c";

function copyText(value?: string): Promise<void> {
  if (!value) {
    return Promise.resolve();
  }

  return navigator.clipboard.writeText(value);
}

function SceneClipCard({ scene, uploadedFileCount }: { scene: StorytellingScene; uploadedFileCount: number }) {
  const displayDuration = scene.durationSec || 4;
  const requiredReferenceIds = Array.from(
    new Set(scene.keyframePrompts.flatMap((prompt) => prompt.productReferenceIds)),
  );

  return (
    <article className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-black uppercase tracking-wide text-rose-600">Scene {scene.sceneIndex} / {displayDuration}s clip</p>
          <h5 className="mt-1 text-xl font-black text-slate-950">{scene.title}</h5>
          <p className="mt-2 text-sm leading-6 text-slate-600">{scene.sceneGoal}</p>
        </div>
        <a className="btn-secondary" href={GOOGLE_FLOW_URL} target="_blank" rel="noreferrer">
          Open Flow
        </a>
      </div>

      <div className="mt-5 grid gap-3 lg:grid-cols-3">
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="field-label">Use these references</p>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            {uploadedFileCount ? `${uploadedFileCount} project image reference(s) are available.` : "Use references generated or selected inside Flow."}
          </p>
          {requiredReferenceIds.length ? (
            <p className="mt-2 text-xs font-semibold text-teal-700">Plan refs: {requiredReferenceIds.join(", ")}</p>
          ) : null}
        </div>
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="field-label">Scene action</p>
          <p className="mt-2 text-sm font-semibold leading-6 text-slate-900">{scene.visualAction}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="field-label">Camera</p>
          <p className="mt-2 text-sm font-semibold text-slate-900">{scene.camera?.selected || "Vertical UGC shot"}</p>
          <p className="mt-1 text-sm leading-6 text-slate-700">{scene.camera?.movement || "Natural movement"}</p>
        </div>
      </div>

      {scene.keyframePrompts.length ? (
        <div className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="field-label">Reference image checklist</p>
          <div className="mt-3 grid gap-3 lg:grid-cols-2">
            {scene.keyframePrompts.map((prompt, index) => (
              <div key={prompt.id} className="rounded-lg border border-slate-200 bg-white p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-xs font-black uppercase tracking-wide text-slate-400">Reference {index + 1} / {prompt.timing}</p>
                    <p className="mt-1 text-sm font-black text-slate-950">{prompt.label}</p>
                  </div>
                  <button className="btn-secondary px-3 py-1.5 text-xs" type="button" onClick={() => void copyText(prompt.prompt)}>
                    Copy image prompt
                  </button>
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-600">{prompt.purpose}</p>
                {prompt.productReferenceIds.length ? (
                  <p className="mt-2 text-xs font-semibold text-teal-700">Attach: {prompt.productReferenceIds.join(", ")}</p>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="mt-5 grid gap-3 lg:grid-cols-[minmax(0,1.3fr)_minmax(280px,0.7fr)]">
        <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 text-white">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs font-black uppercase tracking-wide text-teal-200">Final 4s video prompt</p>
            <button
              className="rounded-md bg-white/10 px-3 py-1.5 text-xs font-bold text-white transition hover:bg-white/15"
              type="button"
              onClick={() => void copyText(scene.finalVideoPrompt)}
            >
              Copy video prompt
            </button>
          </div>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-100">{scene.finalVideoPrompt}</p>
        </div>

        <div className="space-y-3">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <p className="field-label">Voice / subtitle</p>
            {scene.voiceLines.length ? (
              <div className="mt-3 space-y-2">
                {scene.voiceLines.map((line) => (
                  <div key={`${line.timing}-${line.line}`} className="rounded-md border border-slate-200 bg-white p-3">
                    <p className="text-xs font-bold uppercase tracking-wide text-slate-400">{line.timing} / {line.emotion}</p>
                    <p className="mt-1 text-sm font-semibold leading-6 text-slate-900">{line.line}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-2 text-sm text-slate-500">No voice line specified.</p>
            )}
          </div>
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
            <p className="field-label text-amber-700">Overlay text</p>
            <p className="mt-2 text-sm font-semibold leading-6 text-slate-900">{scene.onScreenText || "No overlay text"}</p>
          </div>
        </div>
      </div>
    </article>
  );
}

export default function ProjectDetailPage({ phase }: ProjectDetailPageProps) {
  const { id } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState<Project | null>(null);
  const [loadingAction, setLoadingAction] = useState<ActionName | null>("load");
  const [error, setError] = useState<string | null>(null);
  const [planPipelineStep, setPlanPipelineStep] = useState<PlanPipelineStep>("scene-plan");
  const productReferenceInputRef = useRef<HTMLInputElement>(null);
  const imageReferenceInputRef = useRef<HTMLInputElement>(null);

  const canAct = Boolean(project && !loadingAction);
  const projectBase = id ? `/projects/${id}` : "/projects";

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

  if (loadingAction === "load" && !project) {
    return <div className="card p-6 text-sm text-slate-500">Loading project...</div>;
  }

  const hasPlanCreation = Boolean(project?.creative_plan);
  const phaseState = (item: ProjectPhase): "current" | "complete" | "ready" => {
    if (item === phase) {
      return "current";
    }
    if (item === "brief") {
      return "complete";
    }
    return hasPlanCreation ? "complete" : "ready";
  };
  const phaseClass = (state: ReturnType<typeof phaseState>) => {
    if (state === "current") {
      return "border-rose-300 bg-rose-50";
    }
    if (state === "complete") {
      return "border-emerald-200 bg-emerald-50";
    }
    return "border-slate-200 bg-white hover:-translate-y-0.5 hover:shadow-soft";
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
    return "Ready";
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

      {error ? <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</div> : null}

      <nav className="card-accent p-4">
        <div className="grid gap-3 md:grid-cols-2">
          {phaseItems.map((item, index) => {
            const state = phaseState(item.id);
            return (
              <Link key={item.id} className={`rounded-lg border p-4 transition ${phaseClass(state)}`} to={`${projectBase}/${item.id}`}>
                <div className="flex items-center justify-between gap-2">
                  <span className={`flex h-8 w-8 items-center justify-center rounded-md text-xs font-black ${phaseBadgeClass(state)}`}>
                    {index + 1}
                  </span>
                  <span className="text-xs font-bold uppercase tracking-wide text-slate-400">{phaseStatusLabel(state)}</span>
                </div>
                <p className="mt-3 text-sm font-black text-slate-950">{item.label}</p>
                <p className="mt-1 text-xs text-slate-500">{item.description}</p>
              </Link>
            );
          })}
        </div>
      </nav>

      {project && phase === "brief" ? (
        <section className="card-accent overflow-hidden">
          <div className="border-b border-slate-200/80 px-6 py-5">
            <p className="text-xs font-bold uppercase tracking-wide text-teal-700">Input package</p>
            <h3 className="section-heading">Brief Input</h3>
            <p className="section-subtitle">Confirm the brief, upload product images, then generate a 4-second scene plan.</p>
          </div>
          <div className="space-y-7 px-6 py-6">
            <div>
              <h4 className="mt-1 text-lg font-black text-slate-950">Confirm brief input</h4>
              <p className="mt-1 text-sm text-slate-500">This is the text context Gemini uses together with the product reference images.</p>
            </div>
            <div className="grid gap-7 lg:grid-cols-2">
              <div className="space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
                <p className="field-label">Product description</p>
                <p className="text-sm leading-7 text-slate-700">{project.product_description || "Not specified"}</p>
                {project.audience ? (
                  <p className="text-sm leading-7 text-slate-700">
                    <span className="font-semibold text-slate-900">Audience:</span> {project.audience}
                  </p>
                ) : null}
              </div>
              <div className="space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
                <p className="field-label">Brief</p>
                <p className="whitespace-pre-wrap text-sm leading-7 text-slate-700">{project.brief || "Not specified"}</p>
              </div>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-5">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <p className="text-xs font-black uppercase tracking-wide text-teal-700">Product images</p>
                  <h4 className="mt-1 text-lg font-black text-slate-950">Upload product references</h4>
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
        <section className="card-accent p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="section-heading">Plan Creation</h3>
              <p className="section-subtitle">Move through one step at a time. Every generated scene is one 4-second video clip.</p>
            </div>
            <button className="btn-primary" disabled={!canAct} onClick={() => void runPlanCreation()} type="button">
              {loadingAction === "planCreation" ? "Generating..." : hasPlanCreation ? "Regenerate 4s Plan Creation" : "Generate 4s Plan Creation"}
            </button>
          </div>

          {project?.creative_plan ? (
            <div className="mb-4 grid gap-3 md:grid-cols-3">
              <button
                className={`rounded-lg border p-4 text-left transition ${
                  planPipelineStep === "scene-plan" ? "border-rose-300 bg-rose-50" : "border-emerald-200 bg-emerald-50"
                }`}
                onClick={() => setPlanPipelineStep("scene-plan")}
                type="button"
              >
                <p className="text-xs font-black uppercase tracking-wide text-slate-400">Step</p>
                <p className="mt-1 text-sm font-black text-slate-950">Review 4s scene plan</p>
                <p className="mt-1 text-xs text-slate-500">Check how the script was split.</p>
              </button>
              <button
                className={`rounded-lg border p-4 text-left transition ${
                  planPipelineStep === "image-references" ? "border-rose-300 bg-rose-50" : "border-slate-200 bg-white hover:border-teal-300"
                }`}
                onClick={() => setPlanPipelineStep("image-references")}
                type="button"
              >
                <p className="text-xs font-black uppercase tracking-wide text-slate-400">Step</p>
                <p className="mt-1 text-sm font-black text-slate-950">Upload clip references</p>
                <p className="mt-1 text-xs text-slate-500">Attach generated keyframes or Flow refs.</p>
              </button>
              <button
                className={`rounded-lg border p-4 text-left transition ${
                  planPipelineStep === "scene-clips" ? "border-rose-300 bg-rose-50" : "border-slate-200 bg-white hover:border-teal-300"
                }`}
                onClick={() => setPlanPipelineStep("scene-clips")}
                type="button"
              >
                <p className="text-xs font-black uppercase tracking-wide text-slate-400">Step</p>
                <p className="mt-1 text-sm font-black text-slate-950">Generate 4s clips</p>
                <p className="mt-1 text-xs text-slate-500">Copy one prompt per clip into Flow.</p>
              </button>
            </div>
          ) : null}

          {planPipelineStep === "scene-plan" ? (
            <>
              <PlanCreationCard planCreation={project?.creative_plan} />
              {project?.creative_plan ? (
                <div className="mt-5 flex justify-end border-t border-slate-200 pt-5">
                  <button className="btn-primary" type="button" onClick={() => setPlanPipelineStep("image-references")}>
                    Next
                  </button>
                </div>
              ) : null}
            </>
          ) : null}

          {planPipelineStep === "image-references" ? (
            <div className="rounded-lg border border-slate-200 bg-white p-5">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <p className="text-xs font-black uppercase tracking-wide text-teal-700">Clip references</p>
                  <h4 className="mt-1 text-lg font-black text-slate-950">Upload generated reference images</h4>
                  <p className="mt-1 text-sm leading-6 text-slate-500">
                    Upload generated keyframes here for automation, or create/select them directly in Google Flow. Next step: generate one 4-second clip per scene.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <a className="btn-secondary" href={GOOGLE_FLOW_URL} target="_blank" rel="noreferrer">
                    Open Flow
                  </a>
                  <button className="btn-primary" disabled={!canAct} type="button" onClick={() => imageReferenceInputRef.current?.click()}>
                    {loadingAction === "upload" ? "Uploading..." : "Upload Clip References"}
                  </button>
                </div>
                <input
                  ref={imageReferenceInputRef}
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

              {project?.uploaded_files.length ? (
                <div className="mt-5 border-t border-slate-200 pt-5">
                  <p className="field-label">Uploaded project references</p>
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
              ) : null}

              <div className="mt-5 flex justify-between border-t border-slate-200 pt-5">
                <button className="btn-secondary" type="button" onClick={() => setPlanPipelineStep("scene-plan")}>
                  Back
                </button>
                <button className="btn-primary" type="button" onClick={() => setPlanPipelineStep("scene-clips")}>
                  Next
                </button>
              </div>
            </div>
          ) : null}

          {planPipelineStep === "scene-clips" ? (
            <div className="rounded-lg border border-slate-200 bg-white p-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-black uppercase tracking-wide text-teal-700">Scene clips</p>
                  <h4 className="mt-1 text-lg font-black text-slate-950">Generate each 4-second clip</h4>
                  <p className="mt-1 text-sm leading-6 text-slate-500">
                    For each scene, attach the matching reference images, copy the final 4s video prompt, and generate one vertical clip in Flow or your video model.
                  </p>
                </div>
                <a className="btn-primary" href={GOOGLE_FLOW_URL} target="_blank" rel="noreferrer">
                  Open Google Flow
                </a>
              </div>

              <div className="mt-5 grid gap-3 lg:grid-cols-3">
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <p className="field-label">Use references</p>
                  <p className="mt-2 text-sm leading-6 text-slate-700">Add the uploaded images or the references you created directly inside Flow.</p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <p className="field-label">Paste prompt</p>
                  <p className="mt-2 text-sm leading-6 text-slate-700">Use the final 4s video prompt for the current scene only.</p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <p className="field-label">Repeat per scene</p>
                  <p className="mt-2 text-sm leading-6 text-slate-700">Generate one 4-second clip per scene, then stitch the clips in your editor.</p>
                </div>
              </div>

              <div className="mt-5 space-y-4">
                {project?.creative_plan?.scenes?.map((scene) => (
                  <SceneClipCard key={scene.sceneIndex} scene={scene} uploadedFileCount={project.uploaded_files.length} />
                ))}
              </div>

              <div className="mt-5 flex justify-between border-t border-slate-200 pt-5">
                <button className="btn-secondary" type="button" onClick={() => setPlanPipelineStep("image-references")}>
                  Back
                </button>
                <button className="btn-primary" type="button" onClick={() => setPlanPipelineStep("scene-plan")}>
                  Back to scene plan
                </button>
              </div>
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
