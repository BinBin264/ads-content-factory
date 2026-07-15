import { useEffect, useRef, useState } from "react";
import { toApiUrl } from "../api/client";
import type {
  ImageGenerationJob,
  ImageModelId,
  KeyframePrompt,
  PlanCreation,
  ProductReference,
  ReferenceAsset,
  ReviewKeyframePayload,
  ReviewSceneTakePayload,
  StorytellingScene,
  UploadedFileInfo,
  VideoModelId,
} from "../types";

export type PlanWorkflowStep = "reference-assets" | "keyframes" | "scene-clips";
export type PlanProductionMode = "manual" | "automation";
type ReferenceAssetType = "character" | "location";
const DEFAULT_SCENE_DURATION_SECONDS = 8;
const ACTIVE_IMAGE_JOB_STATUSES = new Set(["queued", "running", "retrying"]);

const IMAGE_MODEL_OPTIONS: Array<{
  id: ImageModelId;
  group: "Google / Nano Banana" | "OpenAI / GPT Image";
  label: string;
  summary: string;
  buttonLabel: string;
}> = [
  {
    id: "nano-banana-2",
    group: "Google / Nano Banana",
    label: "Nano Banana 2",
    summary: "Balanced default for 9:16 reference-guided production images with 2K output.",
    buttonLabel: "Nano Banana 2",
  },
  {
    id: "nano-banana-pro",
    group: "Google / Nano Banana",
    label: "Nano Banana Pro",
    summary: "Highest-detail option for difficult character, location, and product consistency shots.",
    buttonLabel: "Nano Banana Pro",
  },
  {
    id: "nano-banana",
    group: "Google / Nano Banana",
    label: "Nano Banana",
    summary: "Fast base model for drafts and inexpensive visual exploration before final generation.",
    buttonLabel: "Nano Banana",
  },
  {
    id: "gpt-image-2-all",
    group: "OpenAI / GPT Image",
    label: "GPT Image 2 All",
    summary: "Generation and editing model for reference-guided images on a 2:3 portrait canvas with a centered 9:16 safe crop.",
    buttonLabel: "GPT Image 2 All",
  },
  {
    id: "gpt-image-2",
    group: "OpenAI / GPT Image",
    label: "GPT Image 2",
    summary: "Reference-guided GPT Image generation on a 2:3 portrait canvas with a centered 9:16 safe crop.",
    buttonLabel: "GPT Image 2",
  },
  {
    id: "gpt-image-1.5",
    group: "OpenAI / GPT Image",
    label: "GPT Image 1.5",
    summary: "Detailed GPT Image option for reference edits; outputs 2:3 portrait with a protected 9:16 safe area.",
    buttonLabel: "GPT Image 1.5",
  },
  {
    id: "gpt-image-1",
    group: "OpenAI / GPT Image",
    label: "GPT Image 1",
    summary: "Base GPT Image model with image-to-image references and a 2:3 portrait output canvas.",
    buttonLabel: "GPT Image 1",
  },
];

const VIDEO_MODEL_OPTIONS: Array<{
  id: VideoModelId;
  label: string;
  summary: string;
  buttonLabel: string;
}> = [
  {
    id: "veo3.1-pro",
    label: "Veo 3.1 Pro",
    summary: "9:16 portrait, first-frame image-to-video, highest-quality Veo option.",
    buttonLabel: "Veo Pro",
  },
  {
    id: "veo3.1-fast",
    label: "Veo 3.1 Fast",
    summary: "9:16 portrait, first-frame image-to-video, faster Veo generation.",
    buttonLabel: "Veo Fast",
  },
  {
    id: "grok-video-3",
    label: "Grok Video 3",
    summary: "2:3 portrait image-to-video at 1080P; uses the scene duration.",
    buttonLabel: "Grok Video 3",
  },
  {
    id: "grok-video-3-10s",
    label: "Grok Video 3 - 10s",
    summary: "2:3 portrait image-to-video at 1080P with a fixed 10-second output.",
    buttonLabel: "Grok 10s",
  },
];

function videoModelOption(modelId: VideoModelId) {
  return VIDEO_MODEL_OPTIONS.find((option) => option.id === modelId) || VIDEO_MODEL_OPTIONS[0];
}

function imageModelOption(modelId: ImageModelId) {
  return IMAGE_MODEL_OPTIONS.find((option) => option.id === modelId) || IMAGE_MODEL_OPTIONS[0];
}

function ImageModelSelector({
  onChange,
  value,
}: {
  onChange: (model: ImageModelId) => void;
  value: ImageModelId;
}) {
  const selected = imageModelOption(value);
  return (
    <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
      <label className="field-label text-blue-900" htmlFor="image-model-selector">Image generation model</label>
      <select
        id="image-model-selector"
        className="input-control mt-2 bg-white"
        value={value}
        onChange={(event) => onChange(event.target.value as ImageModelId)}
      >
        {(["Google / Nano Banana", "OpenAI / GPT Image"] as const).map((group) => (
          <optgroup key={group} label={group}>
            {IMAGE_MODEL_OPTIONS.filter((option) => option.group === group).map((option) => (
              <option key={option.id} value={option.id}>{option.label}</option>
            ))}
          </optgroup>
        ))}
      </select>
      <p className="mt-2 text-xs leading-5 text-blue-900">{selected.summary}</p>
    </div>
  );
}

interface PlanCreationCardProps {
  planCreation?: PlanCreation | null;
  step: PlanWorkflowStep;
  mode: PlanProductionMode;
  uploadedFiles: UploadedFileInfo[];
  googleFlowUrl: string;
  generatingClipSceneIndex?: number | null;
  imageGenerationJobs?: Record<string, ImageGenerationJob>;
  submittingImageTargets?: Set<string>;
  isReviewingTake?: boolean;
  isUploadingClip?: boolean;
  isUploadingReferenceAsset?: boolean;
  isUploadingKeyframe?: boolean;
  selectedVideoModel: VideoModelId;
  selectedImageModel: ImageModelId;
  onSelectedImageModelChange: (model: ImageModelId) => void;
  onSelectedVideoModelChange: (model: VideoModelId) => void;
  onGenerateClip?: (sceneIndex: number, prompt: string, model: VideoModelId, force?: boolean) => void;
  onGenerateKeyframe?: (sceneIndex: number, slotId: string, prompt: string, model: ImageModelId) => void;
  onGenerateReferenceAsset?: (assetType: ReferenceAssetType, imagePrompt: string, model: ImageModelId) => void;
  onReviewKeyframe?: (sceneIndex: number, slotId: string, payload: ReviewKeyframePayload) => void;
  onUploadClip?: (sceneIndex: number, file: File) => void;
  onUploadKeyframe?: (sceneIndex: number, slotId: string, file: File) => void;
  onUploadReferenceAsset?: (assetType: ReferenceAssetType, file: File) => void;
  onReviewTake?: (sceneIndex: number, payload: ReviewSceneTakePayload) => void;
}

function GenerationButton({
  disabled,
  isGenerating,
  isSubmitting,
  job,
  label,
  loadingLabel,
  onClick,
  providerProgress,
  providerStatus,
}: {
  disabled?: boolean;
  isGenerating?: boolean;
  isSubmitting?: boolean;
  job?: ImageGenerationJob;
  label: string;
  loadingLabel?: string;
  onClick: () => void;
  providerProgress?: number | null;
  providerStatus?: string | null;
}) {
  const isActive = Boolean(job && ACTIVE_IMAGE_JOB_STATUSES.has(job.status));
  const hasProviderProgress = isGenerating && typeof providerProgress === "number";
  const isTrackedJob = Boolean(isSubmitting || isActive || hasProviderProgress);
  const isWorking = Boolean(isTrackedJob || isGenerating);
  const progress = isSubmitting
    ? 0
    : Math.max(0, Math.min(100, hasProviderProgress ? providerProgress : job?.progress ?? 0));
  const statusLabel = hasProviderProgress
    ? `${providerStatus === "QUEUED" ? "Queued" : "Provider processing"} - ${progress}%`
    : isGenerating && !isTrackedJob
    ? loadingLabel || "Generating..."
    : isSubmitting
    ? "Submitting - 0%"
    : job?.status === "queued"
      ? `${job.phase} - ${progress}%`
      : job?.status === "retrying"
        ? `${job.phase} - ${progress}%`
        : `${job?.phase || "Generating"} - ${progress}%`;

  return (
    <>
      <button
        aria-busy={isWorking}
        className={`btn-primary generation-action mt-3 w-full ${isWorking ? "is-loading" : ""}`}
        disabled={disabled || isWorking}
        type="button"
        onClick={onClick}
      >
        {isTrackedJob ? <span aria-hidden="true" className="generation-action-bar" style={{ width: `${progress}%` }} /> : null}
        {isGenerating && !isTrackedJob ? <span aria-hidden="true" className="generation-action-bar is-indeterminate" /> : null}
        <span className="generation-action-label">{isWorking ? statusLabel : label}</span>
      </button>
      {job?.status === "failed" ? (
        <p className="mt-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs leading-5 text-rose-800">
          {job.error || "Image generation failed. You can retry this image."}
        </p>
      ) : null}
    </>
  );
}

function copyText(value: string): Promise<void> {
  return navigator.clipboard.writeText(value);
}

function cleanFileLabel(fileName: string): string {
  const withoutExtension = fileName.replace(/\.[^.]+$/, "");
  const withoutTimestamp = withoutExtension.replace(/_[0-9]{8,14}$/, "");
  const withoutNestedExtension = withoutTimestamp.replace(/\.[^.]+$/, "");
  const words = withoutNestedExtension.replace(/[^a-zA-Z0-9]+/g, " ").trim();
  if (!words) {
    return "Product Reference";
  }
  return words
    .split(/\s+/)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

function slug(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "reference";
}

function outputFileName(prefix: string, index: number): string {
  return `${prefix}_${String(index).padStart(2, "0")}.png`;
}

function primaryKeyframes(scene: StorytellingScene): KeyframePrompt[] {
  return scene.keyframePrompts || [];
}

function sceneDuration(scene: StorytellingScene): number {
  return scene.durationSec || DEFAULT_SCENE_DURATION_SECONDS;
}

function sceneClipOutputName(scene: StorytellingScene): string {
  return `scene_${String(scene.sceneIndex).padStart(2, "0")}_clip_${sceneDuration(scene)}s.mp4`;
}

function cleanVideoPrompt(value: string): string {
  return value
    .replace(/^\s*Create\s+(?:exactly\s+)?(?:one\s+)?(?:an?\s+)?\d+\s*[- ]seconds?\s+(?:vertical\s+)?(?:\d+:\d+\s+)?(?:ad\s+)?(?:video|clip)\.?\s*/i, "")
    .replace(/\bCreate an? \d+\s*[- ]seconds? vertical video\.\s*/gi, "")
    .replace(/\bexact(?:ly)? \d+\s*[- ]seconds? duration,?\s*/gi, "")
    .trim();
}

function replaceReferenceIds(value: string, references: Map<string, string>): string {
  let nextValue = value;
  references.forEach((mention, id) => {
    nextValue = nextValue.split(id).join(mention);
  });
  return nextValue;
}

function keyframeSourcePrompt(value: string): string {
  const referenceHeader = "Reference images to attach / mention in Flow:";
  let source = value.trim();
  while (source.startsWith(referenceHeader)) {
    const boundary = source.indexOf("\n\n");
    if (boundary < 0) {
      return "";
    }
    source = source.slice(boundary + 2).trimStart();
  }

  const compiledMarkers = ["\n\nAction:", "\n\nProduct moment:", "\n\nCamera:", "\n\nPreservation rule:"];
  const firstCompiledSection = compiledMarkers
    .map((marker) => source.indexOf(marker))
    .filter((index) => index >= 0)
    .sort((left, right) => left - right)[0];
  return (firstCompiledSection === undefined ? source : source.slice(0, firstCompiledSection)).trim();
}

function buildKeyframePromptText(scene: StorytellingScene, prompt: KeyframePrompt, referenceMentions: string[], productMentions: Map<string, string>): string {
  const routedBindings = (prompt.referenceBindings || []).filter((binding) => binding.stage === "keyframe");
  const fallbackMentions = referenceMentions.map((mention) => ({
    tag: mention,
    transfer: "the relevant product/app state only",
    ignore: "hands, people, background, camera, motion, and unrelated screen states",
  }));
  const referenceLines = (routedBindings.length ? routedBindings : fallbackMentions).map(
    (binding) => `- ${binding.tag}: transfer only ${binding.transfer}; ignore ${binding.ignore}.`,
  );
  const referenceBlock = referenceLines.length
    ? ["Reference images to attach / mention in Flow:", ...referenceLines].join("\n")
    : "No reference image is required for this opening keyframe.";
  const parts = [
    referenceBlock,
    scene.openingState ? `Opening frame state: ${replaceReferenceIds(scene.openingState, productMentions)}` : "",
    replaceReferenceIds(keyframeSourcePrompt(prompt.prompt), productMentions),
    scene.camera?.selected || scene.camera?.composition
      ? `Still camera and composition: ${[scene.camera?.selected, scene.camera?.composition].filter(Boolean).join(", ")}`
      : "",
    "Opening-keyframe rules: show frame 0 before the action begins. Exactly one primary actor when present, two natural hands total, one clear owner per prop, and one product/UI state. Do not show the completed scene action, duplicate a person, mirror handedness, create a collage, or redesign any routed reference.",
  ];
  return parts.filter(Boolean).join("\n\n");
}

function buildClipPromptText(scene: StorytellingScene): string {
  return cleanVideoPrompt(scene.finalVideoPrompt) || scene.finalVideoPrompt;
}

function productReferenceLabel(reference: ProductReference, index: number, uploadedFiles: UploadedFileInfo[]): string {
  if (reference.referenceLabel) {
    return reference.referenceLabel;
  }

  const uploadedFile = uploadedFiles.find((file) => file.id === reference.id);
  const uploadedStem = uploadedFile?.file_name.replace(/\.[^.]+$/, "");
  if (uploadedStem && /^product_ref_\d+_/i.test(uploadedStem)) {
    return slug(uploadedStem);
  }
  const baseName = uploadedFile ? cleanFileLabel(uploadedFile.file_name) : reference.name || reference.id;
  return `product_ref_${String(index + 1).padStart(2, "0")}_${slug(baseName)}`;
}

function productReferenceLookup(references: ProductReference[] | undefined, uploadedFiles: UploadedFileInfo[]): Map<string, string> {
  const lookup = new Map<string, string>();
  references?.forEach((reference, index) => {
    lookup.set(reference.id, productReferenceLabel(reference, index, uploadedFiles));
  });
  uploadedFiles.forEach((file, index) => {
    if (!lookup.has(file.id)) {
      lookup.set(file.id, `product_ref_${String(index + 1).padStart(2, "0")}_${slug(cleanFileLabel(file.file_name))}`);
    }
  });
  return lookup;
}

function productReferenceMentionLookup(references: ProductReference[] | undefined, uploadedFiles: UploadedFileInfo[]): Map<string, string> {
  const lookup = new Map<string, string>();
  references?.forEach((reference, index) => {
    const uploadedFile = uploadedFiles.find((file) => file.id === reference.id);
    const fileName = uploadedFile?.file_name || reference.sourceFileName || `${productReferenceLabel(reference, index, uploadedFiles)}.png`;
    lookup.set(reference.id, `@${fileName}`);
  });
  uploadedFiles.forEach((file) => {
    if (!lookup.has(file.id)) {
      lookup.set(file.id, `@${file.file_name}`);
    }
  });
  return lookup;
}

function CopyBlock({
  disabled = false,
  label,
  value,
  tone = "light",
  variant = "default",
}: {
  disabled?: boolean;
  label: string;
  value?: string;
  tone?: "dark" | "light";
  variant?: "default" | "compact";
}) {
  if (!value) {
    return null;
  }

  const isDark = tone === "dark";

  return (
    <div className={`rounded-xl border p-4 ${isDark ? "border-slate-800 bg-slate-950 text-white" : "border-slate-200 bg-slate-50 text-slate-900"}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className={`text-[11px] font-semibold uppercase tracking-[0.14em] ${isDark ? "text-blue-200" : "text-slate-500"}`}>{label}</p>
        <button
          className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
            isDark ? "bg-white/10 text-white hover:bg-white/15" : "border border-slate-200 bg-white text-slate-700 hover:border-blue-300 hover:text-blue-700"
          } disabled:cursor-not-allowed disabled:opacity-40`}
          disabled={disabled}
          onClick={() => void copyText(value)}
          type="button"
        >
          Copy
        </button>
      </div>
      <p
        className={`mt-3 overflow-auto whitespace-pre-wrap rounded-lg pr-1 text-sm leading-7 ${
          variant === "compact" ? "h-28" : "max-h-72"
        } ${isDark ? "text-slate-100" : "text-slate-700"}`}
      >
        {value}
      </p>
    </div>
  );
}

function ReferenceChip({ children }: { children: string }) {
  return (
    <span className="inline-flex rounded-lg border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-800">
      {children}
    </span>
  );
}

function ReferenceAssetCard({
  asset,
  assetType,
  generationJob,
  isSubmitting,
  isUploading,
  mode,
  onGenerate,
  onUpload,
  outputName,
  selectedImageModel,
  title,
}: {
  asset?: ReferenceAsset | null;
  assetType: ReferenceAssetType;
  generationJob?: ImageGenerationJob;
  isSubmitting?: boolean;
  isUploading?: boolean;
  mode: PlanProductionMode;
  onGenerate?: (assetType: ReferenceAssetType, imagePrompt: string, model: ImageModelId) => void;
  onUpload?: (assetType: ReferenceAssetType, file: File) => void;
  outputName: string;
  selectedImageModel: ImageModelId;
  title: string;
}) {
  const uploadInputRef = useRef<HTMLInputElement>(null);
  const [editablePrompt, setEditablePrompt] = useState(asset?.imagePrompt ?? "");

  useEffect(() => {
    setEditablePrompt(asset?.imagePrompt ?? "");
  }, [asset?.imagePrompt]);

  if (!asset) {
    return null;
  }

  const uploadLabel = assetType === "character" ? "Upload character image" : "Upload location image";
  const selectedModelOption = imageModelOption(selectedImageModel);

  return (
    <article className="flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-blue-700">{title}</p>
          <h4 className="mt-1 text-lg font-semibold text-slate-950">{outputName}</h4>
        </div>
        <ReferenceChip>{outputName}</ReferenceChip>
      </div>
      {mode === "automation" ? (
        <>
          <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3">
            {asset.imageUrl ? (
              <a href={toApiUrl(asset.imageUrl)} target="_blank" rel="noreferrer">
                <img className="h-56 w-full rounded-lg object-cover" src={toApiUrl(asset.imageUrl)} alt={`${title} result`} />
              </a>
            ) : (
              <div className="flex h-56 items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white text-sm text-slate-500">
                Generated image preview
              </div>
            )}
          </div>
          <div className="mt-4">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <label className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500" htmlFor={`${assetType}-reference-prompt`}>
                Editable image prompt
              </label>
              <textarea
                id={`${assetType}-reference-prompt`}
                className="mt-3 h-32 w-full resize-none rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm leading-6 text-slate-800 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/15"
                value={editablePrompt}
                onChange={(event) => setEditablePrompt(event.target.value)}
              />
              <GenerationButton
                disabled={!onGenerate || !editablePrompt.trim()}
                isSubmitting={isSubmitting}
                job={generationJob}
                label={`Generate with ${selectedModelOption.buttonLabel}`}
                onClick={() => onGenerate?.(assetType, editablePrompt, selectedImageModel)}
              />
              {asset.generationModel ? (
                <p className="mt-2 text-xs text-slate-500">Current image generated with {imageModelOption(asset.generationModel as ImageModelId).label}.</p>
              ) : null}
            </div>
          </div>
        </>
      ) : (
        <>
          {asset.imageUrl ? (
            <a className="mt-3 inline-flex text-sm font-semibold text-blue-700 hover:text-blue-900" href={toApiUrl(asset.imageUrl)} target="_blank" rel="noreferrer">
              Open uploaded reference
            </a>
          ) : null}
          <div className="mt-4">
            <CopyBlock label="Prompt to paste into Flow" value={asset.imagePrompt} variant="compact" />
          </div>
        </>
      )}
      {mode === "manual" ? (
        <div className="mt-auto pt-4">
          <input
            ref={uploadInputRef}
            className="hidden"
            type="file"
            accept="image/*"
            onChange={(event) => {
              const file = event.target.files?.[0];
              event.currentTarget.value = "";
              if (file) {
                onUpload?.(assetType, file);
              }
            }}
          />
          <button
            className="btn-secondary w-full"
            disabled={isUploading || !onUpload}
            type="button"
            onClick={() => uploadInputRef.current?.click()}
          >
            {isUploading ? "Uploading..." : uploadLabel}
          </button>
        </div>
      ) : null}
    </article>
  );
}

function ReferenceAssetsStep({
  googleFlowUrl,
  imageGenerationJobs,
  isUploadingReferenceAsset,
  mode,
  onGenerateReferenceAsset,
  onSelectedImageModelChange,
  onUploadReferenceAsset,
  planCreation,
  selectedImageModel,
  submittingImageTargets,
}: {
  googleFlowUrl: string;
  imageGenerationJobs?: Record<string, ImageGenerationJob>;
  isUploadingReferenceAsset?: boolean;
  mode: PlanProductionMode;
  onGenerateReferenceAsset?: (assetType: ReferenceAssetType, imagePrompt: string, model: ImageModelId) => void;
  onSelectedImageModelChange: (model: ImageModelId) => void;
  onUploadReferenceAsset?: (assetType: ReferenceAssetType, file: File) => void;
  planCreation: PlanCreation;
  selectedImageModel: ImageModelId;
  submittingImageTargets?: Set<string>;
}) {
  return (
    <div className="space-y-5">
      <div className="rounded-2xl border border-blue-200 bg-blue-50/70 p-5">
        <div className={`grid gap-5 ${mode === "automation" ? "xl:grid-cols-[minmax(0,1fr)_360px] xl:items-start" : ""}`}>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-blue-700">{mode === "manual" ? "Manual instruction" : "Automation instruction"}</p>
            <h4 className="mt-1 text-lg font-semibold text-slate-950">Create two base reference images</h4>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">
              {mode === "manual"
                ? "Copy one prompt at a time into your image tool, then upload each result here. Uploaded images are shared with Automation and every later step."
                : "Choose one image model for this run. Character and location jobs can be submitted together; each job retains its selected model while queued."}
            </p>
            <a className="mt-4 inline-flex text-sm font-semibold text-blue-800 hover:text-blue-950" href={googleFlowUrl} target="_blank" rel="noreferrer">
              Open Flow project
            </a>
          </div>
          {mode === "automation" ? (
            <ImageModelSelector onChange={onSelectedImageModelChange} value={selectedImageModel} />
          ) : null}
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <ReferenceAssetCard
          title="Run 1 / Character reference"
          asset={planCreation.primaryCharacter}
          assetType="character"
          generationJob={imageGenerationJobs?.["reference:character"]}
          isSubmitting={submittingImageTargets?.has("reference:character")}
          isUploading={isUploadingReferenceAsset}
          mode={mode}
          onGenerate={onGenerateReferenceAsset}
          onUpload={onUploadReferenceAsset}
          outputName="character_reference.png"
          selectedImageModel={selectedImageModel}
        />
        <ReferenceAssetCard
          title="Run 2 / Location reference"
          asset={planCreation.primaryLocation}
          assetType="location"
          generationJob={imageGenerationJobs?.["reference:location"]}
          isSubmitting={submittingImageTargets?.has("reference:location")}
          isUploading={isUploadingReferenceAsset}
          mode={mode}
          onGenerate={onGenerateReferenceAsset}
          onUpload={onUploadReferenceAsset}
          outputName="location_reference.png"
          selectedImageModel={selectedImageModel}
        />
      </div>
    </div>
  );
}

function KeyframePromptCard({
  generationJob,
  isSubmitting,
  isUploading,
  mode,
  onGenerate,
  onReview,
  onUpload,
  prompt,
  index,
  productLabels,
  productMentions,
  scene,
  sceneIndex,
  selectedImageModel,
}: {
  generationJob?: ImageGenerationJob;
  isSubmitting?: boolean;
  isUploading?: boolean;
  mode: PlanProductionMode;
  onGenerate?: (sceneIndex: number, slotId: string, prompt: string, model: ImageModelId) => void;
  onReview?: (sceneIndex: number, slotId: string, payload: ReviewKeyframePayload) => void;
  onUpload?: (sceneIndex: number, slotId: string, file: File) => void;
  prompt: KeyframePrompt;
  index: number;
  productLabels: Map<string, string>;
  productMentions: Map<string, string>;
  scene: StorytellingScene;
  sceneIndex: number;
  selectedImageModel: ImageModelId;
}) {
  const uploadInputRef = useRef<HTMLInputElement>(null);
  const productReferenceMentions = prompt.productReferenceIds.map((id) => productMentions.get(id) || `@${productLabels.get(id) || id}`);
  const [editablePrompt, setEditablePrompt] = useState(buildKeyframePromptText(scene, prompt, productReferenceMentions, productMentions));
  const outputName = `scene_${String(sceneIndex).padStart(2, "0")}_keyframe_${String(index + 1).padStart(2, "0")}.png`;
  const selectedModelOption = imageModelOption(selectedImageModel);
  const qualityStatus = prompt.qualityGate?.status || (prompt.selectedImageUrl ? "review_required" : "awaiting_image");
  const isAccepted = Boolean(
    prompt.selectedImageUrl
      && prompt.selectedCandidateId
      && !prompt.stale
      && qualityStatus === "accepted"
      && prompt.qualityGate?.acceptedCandidateId === prompt.selectedCandidateId,
  );

  useEffect(() => {
    setEditablePrompt(buildKeyframePromptText(scene, prompt, productReferenceMentions, productMentions));
  }, [
    prompt.prompt,
    prompt.productReferenceIds.join("|"),
    JSON.stringify(prompt.referenceBindings || []),
    prompt.selectedImageUrl,
    scene.openingState,
    scene.camera?.selected,
    scene.camera?.composition,
  ]);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="grid gap-5 xl:grid-cols-[minmax(320px,0.95fr)_minmax(0,1.05fr)]">
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
          {prompt.selectedImageUrl ? (
            <a href={toApiUrl(prompt.selectedImageUrl)} target="_blank" rel="noreferrer">
              <img className="h-[360px] w-full rounded-lg object-cover" src={toApiUrl(prompt.selectedImageUrl)} alt={outputName} />
            </a>
          ) : (
            <div className="flex h-[360px] items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white text-sm text-slate-500">
              Keyframe preview
            </div>
          )}
          {prompt.selectedImageUrl ? (
            <a className="mt-3 inline-flex text-xs font-semibold text-blue-700 hover:text-blue-900" href={toApiUrl(prompt.selectedImageUrl)} target="_blank" rel="noreferrer">
              Open selected keyframe image
            </a>
          ) : null}
        </div>

        <div className="flex min-w-0 flex-col">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="field-label">Scene {sceneIndex} / Keyframe {index + 1}</p>
              <h5 className="mt-1 text-base font-semibold text-slate-950">{outputName}</h5>
              <p className="mt-1 text-xs leading-5 text-slate-500">{prompt.timing} / {prompt.label}</p>
            </div>
            <ReferenceChip>{outputName}</ReferenceChip>
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            {(prompt.referenceBindings || []).filter((binding) => binding.stage === "keyframe").map((binding) => (
              <ReferenceChip key={`${binding.stage}-${binding.tag}`}>{binding.tag}</ReferenceChip>
            ))}
          </div>

          {prompt.selectedImageUrl ? (
            <div className={`mt-3 rounded-xl border p-3 ${isAccepted ? "border-emerald-200 bg-emerald-50" : qualityStatus === "rejected" ? "border-rose-200 bg-rose-50" : "border-amber-200 bg-amber-50"}`}>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="field-label">Keyframe quality gate</p>
                  <p className="mt-1 text-xs leading-5 text-slate-700">
                    {isAccepted
                      ? "Accepted as the visual source for this scene."
                      : qualityStatus === "rejected"
                        ? "Rejected. Adjust the prompt or references, then generate or upload a replacement."
                        : "Check identity count, hands, handedness, prop ownership, UI fidelity, and opening-state timing before continuing."}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    className="btn-secondary"
                    disabled={!onReview}
                    type="button"
                    onClick={() => onReview?.(sceneIndex, prompt.id, { verdict: "reject", defects: ["manual_quality_review_failed"] })}
                  >
                    Reject
                  </button>
                  <button
                    className="btn-primary"
                    disabled={!onReview || isAccepted || Boolean(prompt.stale)}
                    title={prompt.stale ? "Generate or upload a fresh keyframe before accepting it." : undefined}
                    type="button"
                    onClick={() => onReview?.(sceneIndex, prompt.id, { verdict: "accept" })}
                  >
                    {isAccepted ? "Accepted" : "Accept keyframe"}
                  </button>
                </div>
              </div>
            </div>
          ) : null}

          {prompt.stale ? (
            <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800">
              This prompt changed. Create or upload a fresh keyframe reference before clip generation.
            </p>
          ) : null}

          {mode === "automation" ? (
            <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
              <label className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500" htmlFor={`scene-${sceneIndex}-${prompt.id}-prompt`}>
                {isAccepted ? "Accepted keyframe prompt" : "Editable keyframe prompt"}
              </label>
              <textarea
                id={`scene-${sceneIndex}-${prompt.id}-prompt`}
                className={`mt-3 h-36 w-full resize-none rounded-lg border border-slate-200 px-3 py-2 text-sm leading-6 outline-none transition ${
                  isAccepted
                    ? "cursor-default bg-slate-100 text-slate-600"
                    : "bg-white text-slate-800 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/15"
                }`}
                readOnly={isAccepted}
                value={editablePrompt}
                onChange={(event) => setEditablePrompt(event.target.value)}
              />
              {!isAccepted ? (
                <GenerationButton
                  disabled={!onGenerate || !editablePrompt.trim()}
                  isSubmitting={isSubmitting}
                  job={generationJob}
                  label={`Generate with ${selectedModelOption.buttonLabel}`}
                  onClick={() => onGenerate?.(sceneIndex, prompt.id, keyframeSourcePrompt(editablePrompt), selectedImageModel)}
                />
              ) : null}
              {prompt.generationModel ? (
                <p className="mt-2 text-xs text-slate-500">Current image generated with {imageModelOption(prompt.generationModel as ImageModelId).label}.</p>
              ) : null}
            </div>
          ) : (
            <>
              <div className="mt-4">
                <CopyBlock label="Prompt to paste into Flow" value={editablePrompt} variant="compact" />
              </div>
              {!isAccepted ? (
                <div className="mt-auto pt-4">
                  <input
                    ref={uploadInputRef}
                    className="hidden"
                    type="file"
                    accept="image/*"
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      event.currentTarget.value = "";
                      if (file) {
                        onUpload?.(sceneIndex, prompt.id, file);
                      }
                    }}
                  />
                  <button
                    className="btn-secondary w-full"
                    disabled={isUploading || !onUpload}
                    type="button"
                    onClick={() => uploadInputRef.current?.click()}
                  >
                    {isUploading ? "Uploading..." : "Upload keyframe image"}
                  </button>
                </div>
              ) : null}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function KeyframesStep({
  imageGenerationJobs,
  isUploadingKeyframe,
  mode,
  onGenerateKeyframe,
  onReviewKeyframe,
  onSelectedImageModelChange,
  onUploadKeyframe,
  planCreation,
  selectedImageModel,
  submittingImageTargets,
  uploadedFiles,
}: {
  imageGenerationJobs?: Record<string, ImageGenerationJob>;
  isUploadingKeyframe?: boolean;
  mode: PlanProductionMode;
  onGenerateKeyframe?: (sceneIndex: number, slotId: string, prompt: string, model: ImageModelId) => void;
  onReviewKeyframe?: (sceneIndex: number, slotId: string, payload: ReviewKeyframePayload) => void;
  onSelectedImageModelChange: (model: ImageModelId) => void;
  onUploadKeyframe?: (sceneIndex: number, slotId: string, file: File) => void;
  planCreation: PlanCreation;
  selectedImageModel: ImageModelId;
  submittingImageTargets?: Set<string>;
  uploadedFiles: UploadedFileInfo[];
}) {
  const productLabels = productReferenceLookup(planCreation.productReferences, uploadedFiles);
  const productMentions = productReferenceMentionLookup(planCreation.productReferences, uploadedFiles);

  return (
    <div className="space-y-5">
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className={`grid gap-5 ${mode === "automation" ? "xl:grid-cols-[minmax(0,1fr)_360px] xl:items-start" : ""}`}>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-blue-700">{mode === "manual" ? "Manual instruction" : "Automation instruction"}</p>
            <h4 className="mt-1 text-lg font-semibold text-slate-950">Create keyframe references scene by scene</h4>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              {mode === "manual"
                ? "For each scene, create one main keyframe. Attach character_reference.png, location_reference.png, and only the listed visual refs, then upload the generated keyframe so the clip step can use it as the scene anchor."
                : "Choose the model, then queue multiple keyframes. Each job keeps that model even if you change the selector before it finishes."}
            </p>
          </div>
          {mode === "automation" ? (
            <ImageModelSelector onChange={onSelectedImageModelChange} value={selectedImageModel} />
          ) : null}
        </div>
      </div>

      {planCreation.scenes?.map((scene) => (
        <article key={scene.sceneIndex} className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-rose-600">Scene {scene.sceneIndex} / {sceneDuration(scene)}s</p>
              <h5 className="mt-1 text-lg font-semibold text-slate-950">{scene.title}</h5>
              <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-600">{scene.sceneGoal}</p>
            </div>
            <ReferenceChip>{scene.narrativePurpose}</ReferenceChip>
          </div>

          <div className="mt-4 grid gap-4">
            {primaryKeyframes(scene).map((prompt, index) => (
              <KeyframePromptCard
                key={prompt.id}
                index={index}
                generationJob={imageGenerationJobs?.[`keyframe:${scene.sceneIndex}:${prompt.id}`]}
                isSubmitting={submittingImageTargets?.has(`keyframe:${scene.sceneIndex}:${prompt.id}`)}
                isUploading={isUploadingKeyframe}
                mode={mode}
                onGenerate={onGenerateKeyframe}
                onReview={onReviewKeyframe}
                onUpload={onUploadKeyframe}
                productLabels={productLabels}
                productMentions={productMentions}
                prompt={prompt}
                scene={scene}
                sceneIndex={scene.sceneIndex}
                selectedImageModel={selectedImageModel}
              />
            ))}
          </div>
        </article>
      ))}
    </div>
  );
}

function ClipReviewActions({
  canAccept,
  canRegenerate,
  isRegenerating,
  isReviewing,
  onAccept,
  onRegenerate,
  scene,
}: {
  canAccept: boolean;
  canRegenerate: boolean;
  isRegenerating?: boolean;
  isReviewing?: boolean;
  onAccept: () => void;
  onRegenerate: () => void;
  scene: StorytellingScene;
}) {
  if (!scene.videoUrl) {
    return null;
  }

  const accepted = Boolean(scene.takeReview?.accepted ?? scene.takeReview?.canonAccepted);

  return (
    <section className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="field-label">Clip review</p>
          <h6 className="mt-1 text-sm font-semibold text-slate-950">
            {accepted ? "Clip accepted" : "Approve this clip or generate a replacement"}
          </h6>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            Acceptance only marks this clip complete. It does not change later keyframes or prompts.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="btn-primary" disabled={!canAccept || accepted || isReviewing} type="button" onClick={onAccept}>
            {isReviewing ? "Accepting..." : accepted ? "Accepted" : "Accept Clip"}
          </button>
          <button className="btn-secondary" disabled={!canRegenerate || isRegenerating} type="button" onClick={onRegenerate}>
            {isRegenerating ? "Regenerating..." : "Regenerate Clip"}
          </button>
        </div>
      </div>
    </section>
  );
}

function SceneClipPromptCard({
  isGenerating,
  isReviewing,
  isUploading,
  mode,
  onGenerate,
  onReview,
  onUpload,
  productLabels,
  productMentions,
  scene,
  selectedVideoModel,
}: {
  isGenerating?: boolean;
  isReviewing?: boolean;
  isUploading?: boolean;
  mode: PlanProductionMode;
  onGenerate?: (sceneIndex: number, prompt: string, model: VideoModelId, force?: boolean) => void;
  onReview?: (sceneIndex: number, payload: ReviewSceneTakePayload) => void;
  onUpload?: (sceneIndex: number, file: File) => void;
  productLabels: Map<string, string>;
  productMentions: Map<string, string>;
  scene: StorytellingScene;
  selectedVideoModel: VideoModelId;
}) {
  const uploadInputRef = useRef<HTMLInputElement>(null);
  const outputName = sceneClipOutputName(scene);
  const keyframeNames = primaryKeyframes(scene).map((_, index) => `scene_${String(scene.sceneIndex).padStart(2, "0")}_keyframe_${String(index + 1).padStart(2, "0")}.png`);
  const [editablePrompt, setEditablePrompt] = useState(buildClipPromptText(scene));
  const [promptError, setPromptError] = useState<string | null>(null);
  const selectedModelOption = videoModelOption(selectedVideoModel);
  const keyframesAccepted = primaryKeyframes(scene).length > 0 && primaryKeyframes(scene).every(
    (slot) => Boolean(slot.selectedImageUrl)
      && !slot.stale
      && slot.qualityGate?.status === "accepted"
      && slot.qualityGate.acceptedCandidateId === slot.selectedCandidateId,
  );
  useEffect(() => {
    setEditablePrompt(buildClipPromptText(scene));
    setPromptError(null);
  }, [scene.finalVideoPrompt]);

  const submitGeneration = (force = false) => {
    const cleanedPrompt = editablePrompt.trim();
    if (!cleanedPrompt) {
      setPromptError("Video prompt is empty. Regenerate the scene prompt or type a prompt before generating.");
      return;
    }
    setPromptError(null);
    onGenerate?.(scene.sceneIndex, cleanedPrompt, selectedVideoModel, force);
  };

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="grid items-start gap-5 xl:grid-cols-[minmax(320px,0.95fr)_minmax(0,1.05fr)]">
        <div className="self-start rounded-xl border border-slate-200 bg-slate-50 p-3">
          {scene.videoUrl ? (
            <video className="h-[360px] w-full rounded-lg bg-slate-950 object-cover" controls src={toApiUrl(scene.videoUrl)} />
          ) : (
            <div className="flex h-[360px] items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white text-sm text-slate-500">
              {sceneDuration(scene)}s clip preview
            </div>
          )}
          {scene.videoUrl ? (
            <a className="mt-3 inline-flex text-xs font-semibold text-blue-700 hover:text-blue-900" href={toApiUrl(scene.videoUrl)} target="_blank" rel="noreferrer">
              Open uploaded clip
            </a>
          ) : null}

          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <div className="min-h-36 rounded-xl border border-slate-200 bg-white p-3">
              <p className="field-label">Voice / subtitle</p>
              {scene.voiceLines?.length ? (
                <div className="mt-3 max-h-40 space-y-2 overflow-auto">
                  {scene.voiceLines.map((line) => (
                    <div key={`${line.timing}-${line.line}`} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{line.timing} / {line.emotion}</p>
                        <span
                          className={`rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${
                            line.generationMode === "post_voiceover"
                              ? "bg-amber-100 text-amber-800"
                              : "bg-emerald-100 text-emerald-800"
                          }`}
                        >
                          {line.generationMode === "post_voiceover" ? "Post voiceover" : "Native in clip"}
                        </span>
                      </div>
                      <p className="mt-1 text-sm font-semibold leading-6 text-slate-900">{line.line}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-2 text-sm text-slate-500">No voice line specified.</p>
              )}
            </div>
            <div className="min-h-36 rounded-xl border border-amber-200 bg-amber-50 p-3">
              <p className="field-label text-amber-700">Overlay text</p>
              <p className="mt-2 text-sm font-semibold leading-6 text-slate-900">{scene.onScreenText || "No overlay text"}</p>
            </div>
          </div>
        </div>

        <div className="flex min-w-0 flex-col">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-rose-600">Scene {scene.sceneIndex} / {sceneDuration(scene)}s clip</p>
              <h5 className="mt-1 text-base font-semibold text-slate-950">{outputName}</h5>
              <p className="mt-1 text-xs leading-5 text-slate-500">{scene.title}</p>
            </div>
            <ReferenceChip>{outputName}</ReferenceChip>
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            {keyframeNames.map((item) => (
              <ReferenceChip key={item}>{item}</ReferenceChip>
            ))}
          </div>

          {scene.videoError ? (
            <p className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-800">{scene.videoError}</p>
          ) : null}
          {!keyframesAccepted ? (
            <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800">
              Review and accept this scene&apos;s keyframe before generating or manually using the clip prompt.
            </p>
          ) : null}
          {mode === "automation" ? (
            <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
              <label className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500" htmlFor={`scene-${scene.sceneIndex}-clip-prompt`}>
                Editable video prompt
              </label>
              <textarea
                id={`scene-${scene.sceneIndex}-clip-prompt`}
                className="mt-3 h-48 w-full resize-none rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm leading-6 text-slate-800 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/15"
                value={editablePrompt}
                onChange={(event) => {
                  setEditablePrompt(event.target.value);
                  setPromptError(null);
                }}
              />
              {promptError ? (
                <p className="mt-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-800">{promptError}</p>
              ) : null}
              {!scene.videoUrl ? (
                <GenerationButton
                  disabled={!onGenerate || !keyframesAccepted}
                  isGenerating={isGenerating}
                  label={`Generate with ${selectedModelOption.buttonLabel}`}
                  loadingLabel={`Generating with ${selectedModelOption.buttonLabel}...`}
                  onClick={() => submitGeneration(false)}
                  providerProgress={scene.videoProgress}
                  providerStatus={scene.status}
                />
              ) : null}
            </div>
          ) : (
            <>
              <div className="mt-4">
                {keyframesAccepted ? (
                  <CopyBlock label="Prompt to paste into Flow / Kling / video model" value={editablePrompt} tone="dark" />
                ) : (
                  <div className="rounded-xl border border-dashed border-amber-300 bg-amber-50 p-5 text-sm font-semibold text-amber-800">
                    Accept this scene&apos;s fresh keyframe before using its video prompt.
                  </div>
                )}
              </div>
              <div className="mt-auto pt-4">
                <input
                  ref={uploadInputRef}
                  className="hidden"
                  type="file"
                  accept="video/*"
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    event.currentTarget.value = "";
                    if (file) {
                      onUpload?.(scene.sceneIndex, file);
                    }
                  }}
                />
                <button className="btn-secondary w-full" disabled={isUploading || !onUpload || !keyframesAccepted} type="button" onClick={() => uploadInputRef.current?.click()}>
                  {isUploading
                    ? "Uploading..."
                    : scene.videoUrl
                      ? "Upload replacement clip"
                      : `Upload ${sceneDuration(scene)}s clip`}
                </button>
              </div>
            </>
          )}

          {mode === "automation" ? (
            <ClipReviewActions
              canAccept={Boolean(onReview)}
              canRegenerate={Boolean(onGenerate && keyframesAccepted)}
              isRegenerating={isGenerating}
              isReviewing={isReviewing}
              onAccept={() => onReview?.(scene.sceneIndex, { verdict: "keep" })}
              onRegenerate={() => submitGeneration(true)}
              scene={scene}
            />
          ) : null}
        </div>
      </div>
    </article>
  );
}

function SceneClipsStep({
  generatingClipSceneIndex,
  googleFlowUrl,
  isReviewingTake,
  isUploadingClip,
  mode,
  onGenerateClip,
  onReviewTake,
  onUploadClip,
  onSelectedVideoModelChange,
  planCreation,
  selectedVideoModel,
  uploadedFiles,
}: {
  generatingClipSceneIndex?: number | null;
  googleFlowUrl: string;
  isReviewingTake?: boolean;
  isUploadingClip?: boolean;
  mode: PlanProductionMode;
  onGenerateClip?: (sceneIndex: number, prompt: string, model: VideoModelId, force?: boolean) => void;
  onReviewTake?: (sceneIndex: number, payload: ReviewSceneTakePayload) => void;
  onUploadClip?: (sceneIndex: number, file: File) => void;
  onSelectedVideoModelChange: (model: VideoModelId) => void;
  planCreation: PlanCreation;
  selectedVideoModel: VideoModelId;
  uploadedFiles: UploadedFileInfo[];
}) {
  const productLabels = productReferenceLookup(planCreation.productReferences, uploadedFiles);
  const productMentions = productReferenceMentionLookup(planCreation.productReferences, uploadedFiles);
  const selectedModelOption = videoModelOption(selectedVideoModel);

  return (
    <div className="space-y-5">
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px] xl:items-start">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-blue-700">{mode === "manual" ? "Manual instruction" : "Automation instruction"}</p>
            <h4 className="mt-1 text-lg font-semibold text-slate-950">Generate one timed clip per scene</h4>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              {mode === "manual"
                ? "Attach the listed main keyframe image and paste only that scene's final prompt. Generate clips separately so bad scenes can be rerun without losing the whole video."
                : "The selected keyframe is uploaded as the only visual anchor. Choose a provider model below; the backend applies that model's compatible ratio, duration, resolution, and request fields automatically."}
            </p>
          </div>
          {mode === "automation" ? (
            <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
              <label className="field-label text-blue-900" htmlFor="video-model-selector">Video generation model</label>
              <select
                id="video-model-selector"
                className="input-control mt-2 bg-white"
                value={selectedVideoModel}
                onChange={(event) => onSelectedVideoModelChange(event.target.value as VideoModelId)}
              >
                {VIDEO_MODEL_OPTIONS.map((option) => (
                  <option key={option.id} value={option.id}>{option.label}</option>
                ))}
              </select>
              <p className="mt-2 text-xs leading-5 text-blue-900">{selectedModelOption.summary}</p>
            </div>
          ) : (
            <div className="flex justify-start xl:justify-end">
              <a className="btn-primary" href={googleFlowUrl} target="_blank" rel="noreferrer">Open Google Flow</a>
            </div>
          )}
        </div>
      </div>

      {planCreation.scenes?.map((scene) => (
        <SceneClipPromptCard
          key={scene.sceneIndex}
          isGenerating={generatingClipSceneIndex === scene.sceneIndex}
          isReviewing={isReviewingTake}
          isUploading={isUploadingClip}
          mode={mode}
          onGenerate={onGenerateClip}
          onReview={onReviewTake}
          onUpload={onUploadClip}
          productLabels={productLabels}
          productMentions={productMentions}
          scene={scene}
          selectedVideoModel={selectedVideoModel}
        />
      ))}
    </div>
  );
}

export default function PlanCreationCard({
  generatingClipSceneIndex,
  googleFlowUrl,
  imageGenerationJobs,
  isReviewingTake,
  isUploadingClip,
  isUploadingKeyframe,
  isUploadingReferenceAsset,
  mode,
  onGenerateClip,
  onGenerateKeyframe,
  onGenerateReferenceAsset,
  onReviewKeyframe,
  onReviewTake,
  onUploadClip,
  onUploadKeyframe,
  onUploadReferenceAsset,
  onSelectedImageModelChange,
  onSelectedVideoModelChange,
  planCreation,
  selectedImageModel,
  selectedVideoModel,
  step,
  submittingImageTargets,
  uploadedFiles,
}: PlanCreationCardProps) {
  if (!planCreation) {
    return <div className="empty-state">Plan Creation output will appear after generation.</div>;
  }

  if (!planCreation.productAnalysis && !planCreation.scenes?.length) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-5">
        <p className="text-sm font-semibold text-slate-950">{planCreation.main_message}</p>
        <p className="mt-2 text-sm leading-7 text-slate-700">{planCreation.product_truth}</p>
        <p className="mt-3 text-xs text-slate-500">Legacy plan detected. Regenerate Plan Creation to get the step-by-step output.</p>
      </div>
    );
  }

  if (step === "reference-assets") {
    return (
      <ReferenceAssetsStep
        googleFlowUrl={googleFlowUrl}
        imageGenerationJobs={imageGenerationJobs}
        isUploadingReferenceAsset={isUploadingReferenceAsset}
        mode={mode}
        onGenerateReferenceAsset={onGenerateReferenceAsset}
        onSelectedImageModelChange={onSelectedImageModelChange}
        onUploadReferenceAsset={onUploadReferenceAsset}
        planCreation={planCreation}
        selectedImageModel={selectedImageModel}
        submittingImageTargets={submittingImageTargets}
      />
    );
  }

  if (step === "keyframes") {
    return (
      <KeyframesStep
        imageGenerationJobs={imageGenerationJobs}
        isUploadingKeyframe={isUploadingKeyframe}
        mode={mode}
        onGenerateKeyframe={onGenerateKeyframe}
        onReviewKeyframe={onReviewKeyframe}
        onSelectedImageModelChange={onSelectedImageModelChange}
        onUploadKeyframe={onUploadKeyframe}
        planCreation={planCreation}
        selectedImageModel={selectedImageModel}
        submittingImageTargets={submittingImageTargets}
        uploadedFiles={uploadedFiles}
      />
    );
  }

  return (
    <SceneClipsStep
      generatingClipSceneIndex={generatingClipSceneIndex}
      googleFlowUrl={googleFlowUrl}
      isReviewingTake={isReviewingTake}
      isUploadingClip={isUploadingClip}
      mode={mode}
      onGenerateClip={onGenerateClip}
      onReviewTake={onReviewTake}
      onSelectedVideoModelChange={onSelectedVideoModelChange}
      onUploadClip={onUploadClip}
      planCreation={planCreation}
      selectedVideoModel={selectedVideoModel}
      uploadedFiles={uploadedFiles}
    />
  );
}
