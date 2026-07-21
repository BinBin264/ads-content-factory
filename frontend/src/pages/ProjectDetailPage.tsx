import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Link, useNavigate, useParams } from "react-router-dom";
import PlanCreationCard, { type PlanWorkflowStep } from "../components/PlanCreationCard";
import {
  deleteProject,
  enqueueKeyframeSlotImage,
  enqueueReferenceAssetImage,
  generatePlanCreation,
  generateSceneVideo,
  getImageGenerationJob,
  getProject,
  listImageGenerationJobs,
  pollSceneVideo,
  regenerateSceneVideo,
  reviewKeyframe,
  reviewSceneTake,
  updateKeyframePromptSlot,
  updateReferenceAsset,
  updateSceneVideoPrompt,
  uploadKeyframeSlotImage,
  uploadProjectFiles,
  uploadReferenceAssetImage,
  uploadSceneVideo,
  updateProject,
} from "../api/projects";
import { getApiErrorMessage, toApiUrl } from "../api/client";
import type { ImageGenerationJob, ImageModelId, Project, ReviewKeyframePayload, ReviewSceneTakePayload, VideoModelId } from "../types";
import { compactId, formatDate } from "../utils/format";

type ActionName = "load" | "upload" | "saveBrief" | "planCreation" | "referenceAsset" | "keyframe" | "clip" | "review" | "delete";
type ProjectPhase = "brief" | "plan-creation";
type PlanMode = "manual" | "automation";
type ReferenceAssetType = "character" | "location";

const ACTIVE_IMAGE_JOB_STATUSES = new Set(["queued", "running", "retrying"]);
const VIDEO_POLL_INTERVAL_MS = 5000;

function isVideoJobActive(project: Project, sceneIndex: number): boolean {
  const scene = project.creative_plan?.scenes?.find((item) => item.sceneIndex === sceneIndex);
  return Boolean(scene?.videoJobId && !scene.videoUrl && !["FAILED", "VIDEO_READY"].includes(scene.status || ""));
}

function latestJobsByTarget(jobs: ImageGenerationJob[]): Record<string, ImageGenerationJob> {
  return jobs.reduce<Record<string, ImageGenerationJob>>((latest, job) => {
    const existing = latest[job.target_key];
    if (!existing || new Date(job.updated_at).getTime() >= new Date(existing.updated_at).getTime()) {
      latest[job.target_key] = job;
    }
    return latest;
  }, {});
}

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
  const [generatingClipSceneIndex, setGeneratingClipSceneIndex] = useState<number | null>(null);
  const [selectedImageModel, setSelectedImageModel] = useState<ImageModelId>("nano-banana-2");
  const [selectedVideoModel, setSelectedVideoModel] = useState<VideoModelId>("veo3.1-pro");
  const [imageGenerationJobs, setImageGenerationJobs] = useState<Record<string, ImageGenerationJob>>({});
  const [submittingImageTargets, setSubmittingImageTargets] = useState<Set<string>>(new Set());
  const [headerSlot, setHeaderSlot] = useState<HTMLElement | null>(null);
  const [showRegenerateWarning, setShowRegenerateWarning] = useState(false);
  const [briefDraft, setBriefDraft] = useState({ product_description: "", brief: "" });
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
        const [nextProject, jobs] = await Promise.all([getProject(id), listImageGenerationJobs(id)]);
        setProject(nextProject);
        setImageGenerationJobs(latestJobsByTarget(jobs));
      } catch (err) {
        setError(getApiErrorMessage(err));
      } finally {
        setLoadingAction(null);
      }
    };
    void load();
  }, [id]);

  const activeImageJobIds = Object.values(imageGenerationJobs)
    .filter((job) => ACTIVE_IMAGE_JOB_STATUSES.has(job.status))
    .map((job) => job.id)
    .sort()
    .join("|");

  useEffect(() => {
    if (!id || !activeImageJobIds) {
      return;
    }

    let cancelled = false;
    const jobIds = activeImageJobIds.split("|");
    const poll = async () => {
      const results = await Promise.allSettled(jobIds.map((jobId) => getImageGenerationJob(id, jobId)));
      if (cancelled) {
        return;
      }
      const updates = results
        .filter((result): result is PromiseFulfilledResult<ImageGenerationJob> => result.status === "fulfilled")
        .map((result) => result.value);
      const hasTerminalUpdate = updates.some((job) => job.status === "succeeded" || job.status === "failed");
      const nextProject = hasTerminalUpdate ? await getProject(id) : null;
      if (cancelled) {
        return;
      }
      if (updates.length) {
        setImageGenerationJobs((current) => {
          const next = { ...current };
          updates.forEach((job) => {
            next[job.target_key] = job;
          });
          return next;
        });
      }
      if (nextProject) {
        setProject(nextProject);
      }
    };

    void poll();
    const timer = window.setInterval(() => void poll(), 1000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [id, activeImageJobIds]);

  useEffect(() => {
    if (!project) {
      return;
    }
    setBriefDraft({
      product_description: project.product_description ?? "",
      brief: project.brief ?? "",
    });
  }, [project?.id, project?.product_description, project?.brief]);

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

  const handleSaveBrief = async () => {
    if (!id) {
      return;
    }
    setLoadingAction("saveBrief");
    setError(null);
    try {
      const nextProject = await updateProject(id, {
        product_description: briefDraft.product_description,
        brief: briefDraft.brief,
      });
      setProject(nextProject);
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

  const handleGenerateReferenceAsset = async (
    assetType: ReferenceAssetType,
    imagePrompt: string,
    model: ImageModelId,
  ) => {
    if (!id) {
      return;
    }
    const targetKey = `reference:${assetType}`;
    setSubmittingImageTargets((current) => new Set(current).add(targetKey));
    setError(null);
    try {
      await updateReferenceAsset(id, assetType, { imagePrompt });
      const job = await enqueueReferenceAssetImage(id, assetType, model);
      setImageGenerationJobs((current) => ({ ...current, [job.target_key]: job }));
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setSubmittingImageTargets((current) => {
        const next = new Set(current);
        next.delete(targetKey);
        return next;
      });
    }
  };

  const handleGenerateKeyframe = async (
    sceneIndex: number,
    slotId: string,
    prompt: string,
    model: ImageModelId,
  ) => {
    if (!id) {
      return;
    }
    const targetKey = `keyframe:${sceneIndex}:${slotId}`;
    setSubmittingImageTargets((current) => new Set(current).add(targetKey));
    setError(null);
    try {
      await updateKeyframePromptSlot(id, sceneIndex, slotId, { prompt });
      const job = await enqueueKeyframeSlotImage(id, sceneIndex, slotId, model);
      setImageGenerationJobs((current) => ({ ...current, [job.target_key]: job }));
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setSubmittingImageTargets((current) => {
        const next = new Set(current);
        next.delete(targetKey);
        return next;
      });
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

  const handleReviewKeyframe = async (sceneIndex: number, slotId: string, payload: ReviewKeyframePayload) => {
    if (!id) {
      return;
    }
    setLoadingAction("keyframe");
    setError(null);
    try {
      const nextProject = await reviewKeyframe(id, sceneIndex, slotId, payload);
      setProject(nextProject);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoadingAction(null);
    }
  };

  const handleGenerateClip = async (sceneIndex: number, prompt: string, model: VideoModelId, force = false) => {
    if (!id) {
      return;
    }
    setLoadingAction("clip");
    setGeneratingClipSceneIndex(sceneIndex);
    setError(null);
    try {
      await updateSceneVideoPrompt(id, sceneIndex, prompt);
      let nextProject = force
        ? await regenerateSceneVideo(id, sceneIndex, model)
        : await generateSceneVideo(id, sceneIndex, model);
      setProject(nextProject);
      while (isVideoJobActive(nextProject, sceneIndex)) {
        await new Promise((resolve) => window.setTimeout(resolve, VIDEO_POLL_INTERVAL_MS));
        nextProject = await pollSceneVideo(id, sceneIndex);
        setProject(nextProject);
      }
    } catch (err) {
      setError(getApiErrorMessage(err));
      await refreshProject();
    } finally {
      setGeneratingClipSceneIndex(null);
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

  const handleReviewTake = async (sceneIndex: number, payload: ReviewSceneTakePayload) => {
    if (!id) {
      return;
    }
    setLoadingAction("review");
    setError(null);
    try {
      const nextProject = await reviewSceneTake(id, sceneIndex, payload);
      setProject(nextProject);
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
  const isContentCreation = project?.workflow_type === "content_creation";
  const workflowCopy = isContentCreation
    ? {
        modeLabel: "Content Creation",
        categoryFallback: "Content concept",
        briefSubtitle: "Confirm the script, upload optional visual references, then let AI analyze and split it into concrete scenes.",
        descriptionLabel: "Script",
        descriptionPlaceholder: "Describe the complete story: what happens, who appears, the setting, actions, dialogue, mood, and ending.",
        briefPlaceholder: "",
        contextReferences: "visual reference images",
        saveLabel: "Script",
        uploadEyebrow: "Visual references",
        uploadTitle: "Upload visual references",
        uploadDescription:
          "Upload character references, location references, props, style frames, moodboards, or example images. Next step: Gemini splits the idea into concrete scene clips with one keyframe reference per scene.",
        uploadButton: "Upload Visual References",
        uploadedLabel: "Uploaded visual references",
        emptyUpload:
          "You can generate text-only, but character/location/style references make the scene prompts more controllable.",
      }
    : {
        modeLabel: "Video Ads",
        categoryFallback: "General product",
        briefSubtitle: "Confirm the brief, upload product images, then generate a scene plan with one anchor keyframe per scene.",
        descriptionLabel: "Product description",
        descriptionPlaceholder: "Short product context: what it is, who it helps, main benefit, must-preserve product details.",
        briefPlaceholder: "Ad story, scene direction, voice language, spoken lines, must-show details, CTA, avoid claims.",
        contextReferences: "product reference images",
        saveLabel: "Brief",
        uploadEyebrow: "Product images",
        uploadTitle: "Upload product references",
        uploadDescription:
          "Upload app screenshots, product photos, logo, packaging, or UI screens here before Plan Creation. Next step: Gemini splits the brief into multiple concrete scene clips with one keyframe reference per scene.",
        uploadButton: "Upload Product Images",
        uploadedLabel: "Uploaded product references",
        emptyUpload:
          "You can generate text-only, but product screenshots or photos make the scene prompts more usable.",
      };
  const briefChanged = Boolean(
    project &&
      (briefDraft.product_description !== (project.product_description ?? "") ||
        briefDraft.brief !== (project.brief ?? "")),
  );
  const workflowItems: Array<{ id: PlanWorkflowStep; label: string; description: string }> = [
    { id: "reference-assets", label: "Character + location refs", description: "Create or upload two base images" },
    { id: "keyframes", label: "Scene keyframes", description: "Create one anchor ref per scene" },
    {
      id: "scene-clips",
      label: "Scene clips",
      description: planMode === "manual" ? "Upload one clip per scene" : "Generate and accept one clip at a time",
    },
  ];
  const planScenes = project?.creative_plan?.scenes || [];
  const referenceAssetsComplete = Boolean(
    project?.creative_plan?.primaryCharacter?.imageUrl
      && project?.creative_plan?.primaryLocation?.imageUrl,
  );
  const keyframeSlots = project?.creative_plan?.scenes?.flatMap((scene) => scene.keyframePrompts || []) || [];
  const allKeyframesAccepted = Boolean(
    keyframeSlots.length
      && keyframeSlots.every(
        (slot) => Boolean(slot.selectedImageUrl)
          && !slot.stale
          && slot.qualityGate?.status === "accepted"
          && slot.qualityGate.acceptedCandidateId === slot.selectedCandidateId,
      ),
  );
  const allClipsReady = Boolean(
    planScenes.length
      && planScenes.every(
        (scene) => Boolean(scene.videoUrl)
          && (planMode === "manual" || Boolean(scene.takeReview?.accepted ?? scene.takeReview?.canonAccepted)),
      ),
  );
  const workflowCompletion = [referenceAssetsComplete, allKeyframesAccepted, allClipsReady];
  const workflowPrerequisites = [true, referenceAssetsComplete, referenceAssetsComplete && allKeyframesAccepted];
  const currentWorkflowIndex = Math.max(
    0,
    workflowItems.findIndex((item) => item.id === planWorkflowStep),
  );
  const workflowState = (index: number): "current" | "complete" | "ready" | "locked" => {
    if (workflowCompletion[index]) {
      return "complete";
    }
    if (!workflowPrerequisites[index]) {
      return "locked";
    }
    if (index === currentWorkflowIndex) {
      return "current";
    }
    return "ready";
  };
  const previousWorkflowStep = workflowItems[currentWorkflowIndex - 1]?.id;
  const nextWorkflowStep = workflowItems[currentWorkflowIndex + 1]?.id;
  const activeWorkflowItem = workflowItems[currentWorkflowIndex] ?? workflowItems[0];
  const completedWorkflowCount = workflowCompletion.filter(Boolean).length;
  const currentStepComplete = workflowCompletion[currentWorkflowIndex];
  const nextRequirement =
    planWorkflowStep === "reference-assets" && !referenceAssetsComplete
      ? "Add both character and location images to continue."
      : planWorkflowStep === "keyframes" && !allKeyframesAccepted
        ? "Every scene needs a fresh keyframe image that has been accepted."
        : planWorkflowStep === "scene-clips" && !allClipsReady
          ? planMode === "manual"
            ? "Upload one clip for every scene."
            : "Generate each clip, then review and accept it."
          : null;
  const planHeaderPortal =
    phase === "plan-creation" && headerSlot
      ? createPortal(
          <div className="hidden min-w-0 items-center justify-end gap-2 xl:flex">
            <div className="w-[210px] min-w-0">
              <div className="flex items-center justify-between gap-2">
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-blue-700">Plan Creation</p>
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                  Step {currentWorkflowIndex + 1}/{workflowItems.length}
                </span>
              </div>
              <p className="mt-1 truncate text-sm font-semibold text-slate-950">{activeWorkflowItem.label}</p>
              <div className="mt-1.5 h-1 rounded-full bg-slate-100">
                <div
                  className="h-1 rounded-full bg-blue-500 transition-all"
                  style={{ width: `${((currentWorkflowIndex + 1) / workflowItems.length) * 100}%` }}
                />
              </div>
            </div>

            <div className="grid w-[168px] grid-cols-2 rounded-lg border border-slate-200 bg-slate-100 p-0.5">
              <button
                className={`rounded-md px-2 py-1.5 text-xs font-medium transition ${
                  planMode === "manual" ? "bg-slate-950 text-white shadow-sm" : "text-slate-600 hover:text-slate-950"
                }`}
                onClick={() => setPlanMode("manual")}
                type="button"
              >
                Manual
              </button>
              <button
                className={`rounded-md px-2 py-1.5 text-xs font-medium transition ${
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
              This will rebuild the plan from the brief and reset the workflow to the first step. Uploaded references from the brief stay, but character,
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
                {project.product_category || workflowCopy.categoryFallback} / {compactId(project.id)} / Updated {formatDate(project.updated_at)}
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
          <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200/80 px-6 py-5">
            <div>
              <p className="text-xs font-bold uppercase tracking-wide text-blue-700">Input package</p>
              <h3 className="section-heading">Brief Input</h3>
              <p className="section-subtitle">{workflowCopy.briefSubtitle}</p>
            </div>
            {hasPlanCreation ? (
              <button
                className="btn-primary min-w-24"
                disabled={!canAct}
                onClick={() => navigate(`${projectBase}/plan-creation`)}
                type="button"
              >
                Next
              </button>
            ) : null}
          </div>
          <div className="space-y-7 px-6 py-6">
            <div>
              <h4 className="mt-1 text-lg font-semibold text-slate-950">Confirm brief input</h4>
              <p className="mt-1 text-sm text-slate-500">
                This is the text context Gemini uses together with the {workflowCopy.contextReferences}.
              </p>
            </div>
            <div className={`grid gap-7 ${isContentCreation ? "" : "lg:grid-cols-2"}`}>
              <label className="space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
                <span className="field-label">{workflowCopy.descriptionLabel}</span>
                <textarea
                  className={`field-input resize-y bg-white ${isContentCreation ? "min-h-80" : "min-h-36"}`}
                  placeholder={workflowCopy.descriptionPlaceholder}
                  value={briefDraft.product_description}
                  onChange={(event) => setBriefDraft((current) => ({ ...current, product_description: event.target.value }))}
                />
                {project.audience ? (
                  <p className="text-sm leading-7 text-slate-700">
                    <span className="font-semibold text-slate-900">Audience:</span> {project.audience}
                  </p>
                ) : null}
              </label>
              {!isContentCreation ? (
                <label className="space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <span className="field-label">Brief</span>
                  <textarea
                    className="field-input min-h-72 resize-y bg-white"
                    placeholder={workflowCopy.briefPlaceholder}
                    value={briefDraft.brief}
                    onChange={(event) => setBriefDraft((current) => ({ ...current, brief: event.target.value }))}
                  />
                </label>
              ) : null}
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3">
              <p className="text-sm leading-6 text-slate-500">
                {hasPlanCreation
                  ? "Save text changes first, then regenerate Plan Creation when you want the scene plan to use the updated brief."
                  : "Save edits before generating Plan Creation so Gemini uses the latest brief."}
              </p>
              <button className="btn-secondary" disabled={!canAct || !briefChanged} type="button" onClick={() => void handleSaveBrief()}>
                {loadingAction === "saveBrief" ? "Saving..." : briefChanged ? `Save ${workflowCopy.saveLabel} Changes` : `${workflowCopy.saveLabel} Saved`}
              </button>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-blue-700">{workflowCopy.uploadEyebrow}</p>
                  <h4 className="mt-1 text-lg font-semibold text-slate-950">{workflowCopy.uploadTitle}</h4>
                  <p className="mt-1 text-sm leading-6 text-slate-500">
                    {workflowCopy.uploadDescription}
                  </p>
                </div>
                <button className="btn-primary" disabled={!canAct} type="button" onClick={() => productReferenceInputRef.current?.click()}>
                  {loadingAction === "upload" ? "Uploading..." : workflowCopy.uploadButton}
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
                  <p className="field-label">{workflowCopy.uploadedLabel}</p>
                  <div className="mt-3 flex flex-wrap gap-3">
                    {project.uploaded_files.map((file) => (
                      <a
                        key={file.id}
                        className="inline-flex max-w-full items-center rounded-md border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-semibold text-slate-800 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-800"
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
                  {workflowCopy.emptyUpload}
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
                {loadingAction === "planCreation" ? "Generating Plan Creation..." : hasPlanCreation ? "Regenerate Plan Creation" : "Generate Plan Creation"}
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
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-blue-300">Project</p>
                  <h2 className="mt-2 text-[22px] font-semibold leading-tight">{project?.product_name ?? "Project"}</h2>
                  {project ? (
                    <p className="mt-2 text-sm leading-6 text-slate-400">
                      {project.product_category || workflowCopy.categoryFallback} / {compactId(project.id)}
                      <br />
                      Workflow: {workflowCopy.modeLabel}
                      <br />
                      Prompt provider: Gemini
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
                              : state === "locked"
                                ? "cursor-not-allowed border-white/5 bg-white/[0.02] opacity-55"
                                : "border-white/10 bg-white/[0.04] hover:border-blue-300/50 hover:bg-white/[0.07]"
                        }`}
                        disabled={state === "locked"}
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
                              {state === "current" ? "In progress" : state === "complete" ? "Complete" : state === "locked" ? "Locked" : "Ready"}
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
                              className="inline-flex max-w-full items-center rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-700 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-800"
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
                      generatingClipSceneIndex={generatingClipSceneIndex}
                      imageGenerationJobs={imageGenerationJobs}
                      submittingImageTargets={submittingImageTargets}
                      googleFlowUrl={GOOGLE_FLOW_URL}
                      isReviewingTake={loadingAction === "review"}
                      isUploadingClip={loadingAction === "clip"}
                      isUploadingKeyframe={loadingAction === "keyframe"}
                      isUploadingReferenceAsset={loadingAction === "upload"}
                      mode={planMode}
                      selectedImageModel={selectedImageModel}
                      selectedVideoModel={selectedVideoModel}
                      onSelectedImageModelChange={setSelectedImageModel}
                      onSelectedVideoModelChange={setSelectedVideoModel}
                      onGenerateClip={(sceneIndex, prompt, model, force) => void handleGenerateClip(sceneIndex, prompt, model, force)}
                      onGenerateKeyframe={(sceneIndex, slotId, prompt, model) => void handleGenerateKeyframe(sceneIndex, slotId, prompt, model)}
                      onGenerateReferenceAsset={(assetType, imagePrompt, model) => void handleGenerateReferenceAsset(assetType, imagePrompt, model)}
                      onReviewKeyframe={(sceneIndex, slotId, payload) => void handleReviewKeyframe(sceneIndex, slotId, payload)}
                      onReviewTake={(sceneIndex, payload) => void handleReviewTake(sceneIndex, payload)}
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
                      <div className="text-center text-sm font-bold text-slate-500">
                        <span>{completedWorkflowCount} / {workflowItems.length} complete</span>
                        {nextRequirement ? <span className="mt-1 block text-xs font-medium text-amber-700">{nextRequirement}</span> : null}
                      </div>
                      {nextWorkflowStep ? (
                        <button
                          className="btn-primary"
                          disabled={!currentStepComplete}
                          title={nextRequirement || undefined}
                          type="button"
                          onClick={() => setPlanWorkflowStep(nextWorkflowStep)}
                        >
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
                    <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-blue-700">Ready to generate</p>
                    <h4 className="mt-2 text-2xl font-semibold text-slate-950">No Plan Creation yet</h4>
                    <p className="mx-auto mt-3 max-w-2xl text-sm leading-6 text-slate-600">
                      Generate the plan first. The dashboard will then walk through character/location references, scene keyframes, and clip prompts.
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
