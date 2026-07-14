import { useEffect, useRef, useState } from "react";
import { toApiUrl } from "../api/client";
import type { KeyframePrompt, PlanCreation, ProductReference, ReferenceAsset, StorytellingScene, UploadedFileInfo } from "../types";

export type PlanWorkflowStep = "reference-assets" | "keyframes" | "scene-clips";
export type PlanProductionMode = "manual" | "automation";
type ReferenceAssetType = "character" | "location";

interface PlanCreationCardProps {
  planCreation?: PlanCreation | null;
  step: PlanWorkflowStep;
  mode: PlanProductionMode;
  uploadedFiles: UploadedFileInfo[];
  googleFlowUrl: string;
  isGeneratingClip?: boolean;
  isGeneratingReferenceAsset?: boolean;
  isGeneratingKeyframe?: boolean;
  isUploadingClip?: boolean;
  isUploadingReferenceAsset?: boolean;
  isUploadingKeyframe?: boolean;
  onGenerateClip?: (sceneIndex: number, prompt: string) => void;
  onGenerateKeyframe?: (sceneIndex: number, slotId: string, prompt: string) => void;
  onGenerateReferenceAsset?: (assetType: ReferenceAssetType, imagePrompt: string) => void;
  onUploadClip?: (sceneIndex: number, file: File) => void;
  onUploadKeyframe?: (sceneIndex: number, slotId: string, file: File) => void;
  onUploadReferenceAsset?: (assetType: ReferenceAssetType, file: File) => void;
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

function replaceReferenceIds(value: string, references: Map<string, string>): string {
  let nextValue = value;
  references.forEach((mention, id) => {
    nextValue = nextValue.split(id).join(mention);
  });
  return nextValue;
}

function buildKeyframePromptText(scene: StorytellingScene, prompt: KeyframePrompt, referenceMentions: string[], productMentions: Map<string, string>): string {
  const referenceBlock = [
    "Reference images to attach / mention in Flow:",
    "- @character_reference.png: use for the same actor identity and outfit.",
    "- @location_reference.png: use for the same tabletop home setting.",
    ...referenceMentions.map((mention) => `- ${mention}: use for the relevant product/app screen or product detail.`),
  ].join("\n");
  const parts = [
    referenceBlock,
    replaceReferenceIds(prompt.prompt, productMentions),
    scene.visualAction ? `Action: ${replaceReferenceIds(scene.visualAction, productMentions)}` : "",
    scene.productMoment ? `Product moment: ${replaceReferenceIds(scene.productMoment, productMentions)}` : "",
    scene.camera?.selected || scene.camera?.movement
      ? `Camera: ${[scene.camera?.selected, scene.camera?.movement].filter(Boolean).join(", ")}`
      : "",
  ];
  return parts.filter(Boolean).join("\n\n");
}

function buildClipPromptText(scene: StorytellingScene): string {
  const keyframeNames = scene.keyframePrompts.map((_, index) => `scene_${String(scene.sceneIndex).padStart(2, "0")}_keyframe_${String(index + 1).padStart(2, "0")}.png`);
  const outputName = `scene_${String(scene.sceneIndex).padStart(2, "0")}_clip_4s.mp4`;
  const imageInputBlock = keyframeNames.length
    ? ["Image input for Gommo / Flow:", ...keyframeNames.map((mention, index) => `- ${mention}: ${index === 0 ? "first frame / main keyframe" : "end frame keyframe"}.`)].join("\n")
    : "Image input for Gommo / Flow: selected keyframe image.";
  const voiceBlock = scene.voiceLines?.length
    ? [
        "Voice/subtitle text to preserve exactly:",
        ...scene.voiceLines.map((line) => `- ${line.timing} / ${line.emotion}: "${line.line}"`),
      ].join("\n")
    : "Voice/subtitle text: none.";
  const avoidBlock = scene.negativeRules?.length
    ? ["Avoid / negative rules:", ...scene.negativeRules.map((rule) => `- ${rule}`)].join("\n")
    : "";
  const parts = [
    `Output target: ${outputName}`,
    "Create exactly one 4-second vertical 9:16 video clip.",
    imageInputBlock,
    scene.sceneGoal ? `Scene goal: ${scene.sceneGoal}` : "",
    `Main video prompt:\n${scene.finalVideoPrompt}`,
    voiceBlock,
    `Overlay text: ${scene.onScreenText || "No overlay text."}`,
    avoidBlock,
    "Important: The keyframe image already contains the actor, location, and product/app context. Use it as the visual anchor, not as a collage or slideshow. Keep dialogue, overlay intent, camera motion, and negative rules consistent.",
  ];
  return parts.filter(Boolean).join("\n\n");
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
  label,
  value,
  tone = "light",
  variant = "default",
}: {
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
        <p className={`text-[11px] font-semibold uppercase tracking-[0.14em] ${isDark ? "text-teal-200" : "text-slate-500"}`}>{label}</p>
        <button
          className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
            isDark ? "bg-white/10 text-white hover:bg-white/15" : "border border-slate-200 bg-white text-slate-700 hover:border-teal-300 hover:text-teal-700"
          }`}
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
    <span className="inline-flex rounded-lg border border-teal-200 bg-teal-50 px-2.5 py-1 text-xs font-semibold text-teal-800">
      {children}
    </span>
  );
}

function ReferenceAssetCard({
  asset,
  assetType,
  isGenerating,
  isUploading,
  mode,
  onGenerate,
  onUpload,
  outputName,
  title,
}: {
  asset?: ReferenceAsset | null;
  assetType: ReferenceAssetType;
  isGenerating?: boolean;
  isUploading?: boolean;
  mode: PlanProductionMode;
  onGenerate?: (assetType: ReferenceAssetType, imagePrompt: string) => void;
  onUpload?: (assetType: ReferenceAssetType, file: File) => void;
  outputName: string;
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

  return (
    <article className="flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-teal-700">{title}</p>
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
                className="mt-3 h-32 w-full resize-none rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm leading-6 text-slate-800 outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-500/15"
                value={editablePrompt}
                onChange={(event) => setEditablePrompt(event.target.value)}
              />
              <button
                className="btn-primary mt-3 w-full"
                disabled={isGenerating || !onGenerate || !editablePrompt.trim()}
                type="button"
                onClick={() => onGenerate?.(assetType, editablePrompt)}
              >
                {isGenerating ? "Generating..." : "Generate reference image"}
              </button>
            </div>
          </div>
        </>
      ) : (
        <>
          {asset.imageUrl ? (
            <a className="mt-3 inline-flex text-sm font-semibold text-teal-700 hover:text-teal-900" href={toApiUrl(asset.imageUrl)} target="_blank" rel="noreferrer">
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
  isGeneratingReferenceAsset,
  isUploadingReferenceAsset,
  mode,
  onGenerateReferenceAsset,
  onUploadReferenceAsset,
  planCreation,
}: {
  googleFlowUrl: string;
  isGeneratingReferenceAsset?: boolean;
  isUploadingReferenceAsset?: boolean;
  mode: PlanProductionMode;
  onGenerateReferenceAsset?: (assetType: ReferenceAssetType, imagePrompt: string) => void;
  onUploadReferenceAsset?: (assetType: ReferenceAssetType, file: File) => void;
  planCreation: PlanCreation;
}) {
  return (
    <div className="space-y-5">
      <div className="rounded-2xl border border-teal-200 bg-teal-50/70 p-5">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-teal-700">{mode === "manual" ? "Manual instruction" : "Automation instruction"}</p>
        <h4 className="mt-1 text-lg font-semibold text-slate-950">Create two base reference images</h4>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">
          {mode === "manual"
            ? "Copy one prompt at a time into Flow, Gemini image, Nano Banana, or your image tool. Save outputs as character_reference.png and location_reference.png."
            : "Later this step will call an image provider and save character_reference.png plus location_reference.png automatically. For now, use the same prompts manually."}
        </p>
        <a className="mt-4 inline-flex text-sm font-semibold text-teal-800 hover:text-teal-950" href={googleFlowUrl} target="_blank" rel="noreferrer">
          Open Flow project
        </a>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <ReferenceAssetCard
          title="Run 1 / Character reference"
          asset={planCreation.primaryCharacter}
          assetType="character"
          isGenerating={isGeneratingReferenceAsset}
          isUploading={isUploadingReferenceAsset}
          mode={mode}
          onGenerate={onGenerateReferenceAsset}
          onUpload={onUploadReferenceAsset}
          outputName="character_reference.png"
        />
        <ReferenceAssetCard
          title="Run 2 / Location reference"
          asset={planCreation.primaryLocation}
          assetType="location"
          isGenerating={isGeneratingReferenceAsset}
          isUploading={isUploadingReferenceAsset}
          mode={mode}
          onGenerate={onGenerateReferenceAsset}
          onUpload={onUploadReferenceAsset}
          outputName="location_reference.png"
        />
      </div>
    </div>
  );
}

function KeyframePromptCard({
  isGenerating,
  isUploading,
  mode,
  onGenerate,
  onUpload,
  prompt,
  index,
  productLabels,
  productMentions,
  scene,
  sceneIndex,
}: {
  isGenerating?: boolean;
  isUploading?: boolean;
  mode: PlanProductionMode;
  onGenerate?: (sceneIndex: number, slotId: string, prompt: string) => void;
  onUpload?: (sceneIndex: number, slotId: string, file: File) => void;
  prompt: KeyframePrompt;
  index: number;
  productLabels: Map<string, string>;
  productMentions: Map<string, string>;
  scene: StorytellingScene;
  sceneIndex: number;
}) {
  const uploadInputRef = useRef<HTMLInputElement>(null);
  const productReferenceMentions = prompt.productReferenceIds.map((id) => productMentions.get(id) || `@${productLabels.get(id) || id}`);
  const [editablePrompt, setEditablePrompt] = useState(buildKeyframePromptText(scene, prompt, productReferenceMentions, productMentions));
  const outputName = `scene_${String(sceneIndex).padStart(2, "0")}_keyframe_${String(index + 1).padStart(2, "0")}.png`;

  useEffect(() => {
    setEditablePrompt(buildKeyframePromptText(scene, prompt, productReferenceMentions, productMentions));
  }, [prompt.prompt, scene.visualAction, scene.productMoment, scene.camera?.selected, scene.camera?.movement]);

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
            <a className="mt-3 inline-flex text-xs font-semibold text-teal-700 hover:text-teal-900" href={toApiUrl(prompt.selectedImageUrl)} target="_blank" rel="noreferrer">
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
            <ReferenceChip>@character_reference.png</ReferenceChip>
            <ReferenceChip>@location_reference.png</ReferenceChip>
            {prompt.productReferenceIds.map((id) => productMentions.get(id) || `@${productLabels.get(id) || id}`).map((item) => (
              <ReferenceChip key={item}>{item}</ReferenceChip>
            ))}
          </div>

          {prompt.stale ? (
            <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800">
              This prompt changed. Create or upload a fresh keyframe reference before clip generation.
            </p>
          ) : null}

          {mode === "automation" ? (
            <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
              <label className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500" htmlFor={`scene-${sceneIndex}-${prompt.id}-prompt`}>
                Editable keyframe prompt
              </label>
              <textarea
                id={`scene-${sceneIndex}-${prompt.id}-prompt`}
                className="mt-3 h-36 w-full resize-none rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm leading-6 text-slate-800 outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-500/15"
                value={editablePrompt}
                onChange={(event) => setEditablePrompt(event.target.value)}
              />
              <button
                className="btn-primary mt-3 w-full"
                disabled={isGenerating || !onGenerate || !editablePrompt.trim()}
                type="button"
                onClick={() => onGenerate?.(sceneIndex, prompt.id, editablePrompt)}
              >
                {isGenerating ? "Generating..." : "Generate keyframe image"}
              </button>
            </div>
          ) : (
            <>
              <div className="mt-4">
                <CopyBlock label="Prompt to paste into Flow" value={editablePrompt} variant="compact" />
              </div>
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
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function KeyframesStep({
  isGeneratingKeyframe,
  isUploadingKeyframe,
  mode,
  onGenerateKeyframe,
  onUploadKeyframe,
  planCreation,
  uploadedFiles,
}: {
  isGeneratingKeyframe?: boolean;
  isUploadingKeyframe?: boolean;
  mode: PlanProductionMode;
  onGenerateKeyframe?: (sceneIndex: number, slotId: string, prompt: string) => void;
  onUploadKeyframe?: (sceneIndex: number, slotId: string, file: File) => void;
  planCreation: PlanCreation;
  uploadedFiles: UploadedFileInfo[];
}) {
  const productLabels = productReferenceLookup(planCreation.productReferences, uploadedFiles);
  const productMentions = productReferenceMentionLookup(planCreation.productReferences, uploadedFiles);

  return (
    <div className="space-y-5">
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-teal-700">{mode === "manual" ? "Manual instruction" : "Automation instruction"}</p>
        <h4 className="mt-1 text-lg font-semibold text-slate-950">Create keyframe references scene by scene</h4>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
          {mode === "manual"
            ? "For each scene, copy the keyframe prompt, attach character_reference.png, location_reference.png, and the listed product refs, then upload the generated keyframe image if you want the app to store it."
            : "Later the app can generate these keyframes through an image provider. The prompts are already structured so the same actor, location, and product references carry forward."}
        </p>
      </div>

      {planCreation.scenes?.map((scene) => (
        <article key={scene.sceneIndex} className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-rose-600">Scene {scene.sceneIndex} / {scene.durationSec || 4}s</p>
              <h5 className="mt-1 text-lg font-semibold text-slate-950">{scene.title}</h5>
              <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-600">{scene.sceneGoal}</p>
            </div>
            <ReferenceChip>{scene.narrativePurpose}</ReferenceChip>
          </div>

          <div className="mt-4 grid gap-4">
            {scene.keyframePrompts?.map((prompt, index) => (
              <KeyframePromptCard
                key={prompt.id}
                index={index}
                isGenerating={isGeneratingKeyframe}
                isUploading={isUploadingKeyframe}
                mode={mode}
                onGenerate={onGenerateKeyframe}
                onUpload={onUploadKeyframe}
                productLabels={productLabels}
                productMentions={productMentions}
                prompt={prompt}
                scene={scene}
                sceneIndex={scene.sceneIndex}
              />
            ))}
          </div>
        </article>
      ))}
    </div>
  );
}

function TextList({ items }: { items?: string[] }) {
  if (!items?.length) {
    return <p className="mt-2 text-sm text-slate-500">None specified.</p>;
  }

  return (
    <ul className="mt-2 space-y-1 text-sm leading-6 text-slate-700">
      {items.map((item) => (
        <li key={item}>- {item}</li>
      ))}
    </ul>
  );
}

function SceneClipPromptCard({
  isGenerating,
  isUploading,
  mode,
  onGenerate,
  onUpload,
  productLabels,
  productMentions,
  scene,
}: {
  isGenerating?: boolean;
  isUploading?: boolean;
  mode: PlanProductionMode;
  onGenerate?: (sceneIndex: number, prompt: string) => void;
  onUpload?: (sceneIndex: number, file: File) => void;
  productLabels: Map<string, string>;
  productMentions: Map<string, string>;
  scene: StorytellingScene;
}) {
  const uploadInputRef = useRef<HTMLInputElement>(null);
  const outputName = `scene_${String(scene.sceneIndex).padStart(2, "0")}_clip_4s.mp4`;
  const keyframeNames = scene.keyframePrompts.map((_, index) => `scene_${String(scene.sceneIndex).padStart(2, "0")}_keyframe_${String(index + 1).padStart(2, "0")}.png`);
  const [editablePrompt, setEditablePrompt] = useState(buildClipPromptText(scene));
  const [promptError, setPromptError] = useState<string | null>(null);
  const providerLabel = [scene.videoProvider || "79AI", scene.videoModel || "veo_omni", scene.videoRatio || "9:16", `${scene.videoDuration || 4}s`, scene.videoMode || "flash"]
    .filter(Boolean)
    .join(" / ");

  useEffect(() => {
    setEditablePrompt(buildClipPromptText(scene));
    setPromptError(null);
  }, [scene.finalVideoPrompt]);

  const handleGenerateClick = () => {
    const cleanedPrompt = editablePrompt.trim();
    if (!cleanedPrompt) {
      setPromptError("Video prompt is empty. Regenerate the scene prompt or type a prompt before generating.");
      return;
    }
    setPromptError(null);
    onGenerate?.(scene.sceneIndex, cleanedPrompt);
  };

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="grid gap-5 xl:grid-cols-[minmax(320px,0.95fr)_minmax(0,1.05fr)]">
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
          {scene.videoUrl ? (
            <video className="h-[360px] w-full rounded-lg bg-slate-950 object-cover" controls src={toApiUrl(scene.videoUrl)} />
          ) : (
            <div className="flex h-[360px] items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white text-sm text-slate-500">
              4s clip preview
            </div>
          )}
          {scene.videoUrl ? (
            <a className="mt-3 inline-flex text-xs font-semibold text-teal-700 hover:text-teal-900" href={toApiUrl(scene.videoUrl)} target="_blank" rel="noreferrer">
              Open uploaded clip
            </a>
          ) : null}
        </div>

        <div className="flex min-w-0 flex-col">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-rose-600">Scene {scene.sceneIndex} / {scene.durationSec || 4}s clip</p>
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
          {scene.videoJobId || scene.videoProvider || scene.status === "PROCESSING" ? (
            <div className="mt-3 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs leading-5 text-blue-900">
              <span className="font-semibold">Provider:</span> {providerLabel}
              {scene.videoJobId ? (
                <>
                  <br />
                  <span className="font-semibold">Job:</span> {scene.videoJobId}
                </>
              ) : null}
              {scene.status ? (
                <>
                  <br />
                  <span className="font-semibold">Status:</span> {scene.status}
                </>
              ) : null}
            </div>
          ) : null}

          {mode === "automation" ? (
            <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
              <label className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500" htmlFor={`scene-${scene.sceneIndex}-clip-prompt`}>
                Editable 4s video prompt
              </label>
              <textarea
                id={`scene-${scene.sceneIndex}-clip-prompt`}
                className="mt-3 h-48 w-full resize-none rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm leading-6 text-slate-800 outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-500/15"
                value={editablePrompt}
                onChange={(event) => {
                  setEditablePrompt(event.target.value);
                  setPromptError(null);
                }}
              />
              {promptError ? (
                <p className="mt-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-800">{promptError}</p>
              ) : null}
              <button
                className="btn-primary mt-3 w-full"
                disabled={isGenerating || !onGenerate}
                type="button"
                onClick={handleGenerateClick}
              >
                {isGenerating ? "Generating..." : "Generate 4s Omni clip"}
              </button>
            </div>
          ) : (
            <>
              <div className="mt-4">
                <CopyBlock label="Prompt to paste into Flow / Kling / video model" value={editablePrompt} tone="dark" />
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
                <button className="btn-secondary w-full" disabled={isUploading || !onUpload} type="button" onClick={() => uploadInputRef.current?.click()}>
                  {isUploading ? "Uploading..." : "Upload 4s clip"}
                </button>
              </div>
            </>
          )}

          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
              <p className="field-label">Voice / subtitle</p>
              {scene.voiceLines?.length ? (
                <div className="mt-3 max-h-32 space-y-2 overflow-auto">
                  {scene.voiceLines.map((line) => (
                    <div key={`${line.timing}-${line.line}`} className="rounded-lg border border-slate-200 bg-white p-3">
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{line.timing} / {line.emotion}</p>
                      <p className="mt-1 text-sm font-semibold leading-6 text-slate-900">{line.line}</p>
                    </div>
                  ))}
                </div>
            ) : (
              <p className="mt-2 text-sm text-slate-500">No voice line specified.</p>
            )}
            </div>
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-3">
              <p className="field-label text-amber-700">Overlay text</p>
              <p className="mt-2 text-sm font-semibold leading-6 text-slate-900">{scene.onScreenText || "No overlay text"}</p>
            </div>
            <div className="rounded-xl border border-rose-200 bg-rose-50 p-3">
              <p className="field-label text-rose-700">Avoid</p>
              <TextList items={scene.negativeRules} />
            </div>
          </div>
        </div>
      </div>
    </article>
  );
}

function SceneClipsStep({
  googleFlowUrl,
  isGeneratingClip,
  isUploadingClip,
  mode,
  onGenerateClip,
  onUploadClip,
  planCreation,
  uploadedFiles,
}: {
  googleFlowUrl: string;
  isGeneratingClip?: boolean;
  isUploadingClip?: boolean;
  mode: PlanProductionMode;
  onGenerateClip?: (sceneIndex: number, prompt: string) => void;
  onUploadClip?: (sceneIndex: number, file: File) => void;
  planCreation: PlanCreation;
  uploadedFiles: UploadedFileInfo[];
}) {
  const productLabels = productReferenceLookup(planCreation.productReferences, uploadedFiles);
  const productMentions = productReferenceMentionLookup(planCreation.productReferences, uploadedFiles);

  return (
    <div className="space-y-5">
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-teal-700">{mode === "manual" ? "Manual instruction" : "Automation instruction"}</p>
            <h4 className="mt-1 text-lg font-semibold text-slate-950">Generate one 4-second clip per scene</h4>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              {mode === "manual"
                ? "Attach the listed reference images and paste only that scene's final prompt. Generate clips separately so bad scenes can be rerun without losing the whole ad."
                : "This calls the configured 79AI VEO Omni Flash provider scene by scene. Selected keyframe images are uploaded and sent through the images field, with 9:16 ratio and one 4-second clip per scene."}
            </p>
          </div>
          <a className="btn-primary" href={googleFlowUrl} target="_blank" rel="noreferrer">
            Open Google Flow
          </a>
        </div>
      </div>

      {planCreation.scenes?.map((scene) => (
        <SceneClipPromptCard
          key={scene.sceneIndex}
          isGenerating={isGeneratingClip}
          isUploading={isUploadingClip}
          mode={mode}
          onGenerate={onGenerateClip}
          onUpload={onUploadClip}
          productLabels={productLabels}
          productMentions={productMentions}
          scene={scene}
        />
      ))}
    </div>
  );
}

export default function PlanCreationCard({
  googleFlowUrl,
  isGeneratingClip,
  isGeneratingKeyframe,
  isGeneratingReferenceAsset,
  isUploadingClip,
  isUploadingKeyframe,
  isUploadingReferenceAsset,
  mode,
  onGenerateClip,
  onGenerateKeyframe,
  onGenerateReferenceAsset,
  onUploadClip,
  onUploadKeyframe,
  onUploadReferenceAsset,
  planCreation,
  step,
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
        isGeneratingReferenceAsset={isGeneratingReferenceAsset}
        isUploadingReferenceAsset={isUploadingReferenceAsset}
        mode={mode}
        onGenerateReferenceAsset={onGenerateReferenceAsset}
        onUploadReferenceAsset={onUploadReferenceAsset}
        planCreation={planCreation}
      />
    );
  }

  if (step === "keyframes") {
    return (
      <KeyframesStep
        isGeneratingKeyframe={isGeneratingKeyframe}
        isUploadingKeyframe={isUploadingKeyframe}
        mode={mode}
        onGenerateKeyframe={onGenerateKeyframe}
        onUploadKeyframe={onUploadKeyframe}
        planCreation={planCreation}
        uploadedFiles={uploadedFiles}
      />
    );
  }

  return (
    <SceneClipsStep
      googleFlowUrl={googleFlowUrl}
      isGeneratingClip={isGeneratingClip}
      isUploadingClip={isUploadingClip}
      mode={mode}
      onGenerateClip={onGenerateClip}
      onUploadClip={onUploadClip}
      planCreation={planCreation}
      uploadedFiles={uploadedFiles}
    />
  );
}
