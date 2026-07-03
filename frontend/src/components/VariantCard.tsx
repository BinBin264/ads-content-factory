import { useState } from "react";
import type { ReactNode } from "react";
import { toApiUrl } from "../api/client";
import type { CharacterReferencePrompt, EditPlan, ProductionScene, UIOverlayItem, Variant } from "../types";
import { formatList } from "../utils/format";

interface VariantCardProps {
  variant: Variant;
  onExport: () => Promise<void>;
  onRender: () => Promise<void>;
  exporting: boolean;
  rendering: boolean;
  disabled: boolean;
}

async function copyText(value: string): Promise<void> {
  await navigator.clipboard.writeText(value);
}

function CopyButton({ value, label = "Copy" }: { value: string; label?: string }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    await copyText(value);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  };

  return (
    <button className="btn-secondary px-3 py-1 text-xs" type="button" onClick={copy}>
      {copied ? "Copied" : label}
    </button>
  );
}

function EmptyPackage() {
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm font-semibold text-amber-900">
      Generate variants again to create the video production workflow.
    </div>
  );
}

function WorkflowStep({
  number,
  title,
  tool,
  children,
}: {
  number: number;
  title: string;
  tool: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-slate-950 text-sm font-black text-white">{number}</span>
          <div>
            <h4 className="text-base font-black text-slate-950">{title}</h4>
            <p className="mt-1 text-sm leading-6 text-slate-600">{tool}</p>
          </div>
        </div>
      </div>
      {children}
    </section>
  );
}

function PromptBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="mb-2 flex items-center justify-between gap-3">
        <p className="field-label">{label}</p>
        <CopyButton value={value} />
      </div>
      <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-950 p-4 text-sm leading-6 text-slate-50">{value}</pre>
    </div>
  );
}

function buildReferenceCopy(prompt: CharacterReferencePrompt, identityLock: string, basePrompt: string): string {
  return [
    "IDENTITY LOCK",
    identityLock,
    "",
    "BASE CHARACTER",
    basePrompt,
    "",
    `Purpose: ${prompt.purpose}`,
    `Aspect ratio: ${prompt.aspect_ratio}`,
    "",
    "PROMPT",
    prompt.prompt,
    "",
    "NEGATIVE PROMPT",
    prompt.negative_prompt,
    "",
    "NOTES",
    prompt.notes || "None",
  ].join("\n");
}

function buildKeyframeCopy(scene: ProductionScene): string {
  return [
    `Scene ${scene.scene_number} keyframe`,
    `Use references: ${formatList(scene.required_reference_assets)}`,
    "",
    scene.keyframe_prompt,
    "",
    "Negative prompt:",
    scene.negative_prompt,
  ].join("\n");
}

function buildVideoCopy(scene: ProductionScene): string {
  return [
    `Scene ${scene.scene_number} video`,
    `Mode: ${scene.generation_mode}`,
    `Duration: ${scene.duration_seconds}s`,
    `Use references: ${formatList(scene.required_reference_assets)}`,
    "",
    "VIDEO PROMPT",
    scene.video_prompt,
    "",
    "MOTION",
    scene.motion_instruction,
    "",
    "CONSISTENCY",
    scene.consistency_instruction,
    "",
    "NEGATIVE PROMPT",
    scene.negative_prompt,
  ].join("\n");
}

function buildOverlayCopy(scene: ProductionScene): string {
  if (!scene.ui_overlay_plan.length) {
    return `Scene ${scene.scene_number}: no overlay planned.`;
  }

  return scene.ui_overlay_plan
    .map((item) =>
      [
        `${item.overlay_type}: ${item.text}`,
        `Time: ${item.start_time}-${item.end_time}`,
        `Position: ${item.position}`,
        `Style: ${item.style_notes}`,
        `Safety: ${item.safety_notes || "None"}`,
      ].join("\n"),
    )
    .join("\n\n");
}

function buildEditCopy(editPlan: EditPlan): string {
  return [
    `Total duration: ${editPlan.total_duration}`,
    `Pacing: ${editPlan.pacing_notes}`,
    `Music: ${editPlan.music_direction}`,
    `Subtitles: ${editPlan.subtitle_style}`,
    `Export ratios: ${formatList(editPlan.export_ratios)}`,
    "",
    "CUT SEQUENCE",
    editPlan.cut_sequence.join("\n"),
    "",
    "POST-PRODUCTION",
    editPlan.required_post_production_steps.join("\n"),
    "",
    "PLATFORM NOTES",
    editPlan.platform_notes,
  ].join("\n");
}

function OverlayList({ items }: { items: UIOverlayItem[] }) {
  if (!items.length) {
    return <p className="text-sm text-slate-500">No overlay planned for this scene.</p>;
  }

  return (
    <div className="grid gap-2 md:grid-cols-2">
      {items.map((item, index) => (
        <div key={`${item.overlay_type}-${index}`} className="rounded-lg border border-slate-200 bg-white p-3">
          <p className="text-sm font-bold text-slate-950">
            {item.overlay_type}: {item.text}
          </p>
          <p className="mt-1 text-xs font-semibold text-slate-500">
            {item.start_time}-{item.end_time} / {item.position}
          </p>
          <p className="mt-2 text-sm leading-6 text-slate-700">{item.style_notes}</p>
          {item.safety_notes ? <p className="mt-1 text-xs font-semibold text-amber-700">{item.safety_notes}</p> : null}
        </div>
      ))}
    </div>
  );
}

export default function VariantCard({ variant, onExport, onRender, exporting, rendering, disabled }: VariantCardProps) {
  const productionPackage = variant.production_package;

  return (
    <article className="card-accent overflow-hidden">
      <div className="border-b border-slate-200 bg-slate-950 p-5 text-white">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-4xl">
            <p className="text-xs font-black uppercase tracking-wide text-teal-300">Video production workflow</p>
            <h3 className="mt-2 text-xl font-black">{variant.name}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-300">{variant.hook}</p>
          </div>
          <span className="rounded-md border border-white/15 bg-white/10 px-3 py-1 text-xs font-bold uppercase tracking-wide text-white">
            {variant.video_status}
          </span>
        </div>
      </div>

      <div className="space-y-5 p-5">
        {!productionPackage ? <EmptyPackage /> : null}

        {productionPackage ? (
          <>
            <WorkflowStep number={1} title="Create character reference images" tool="Use an image generation model first. These images lock the creator identity before video generation.">
              <div className="mb-4 rounded-lg border border-teal-200 bg-teal-50 p-4">
                <p className="field-label text-teal-700">Character lock</p>
                <p className="mt-2 text-sm leading-6 text-slate-800">{productionPackage.character_bible.identity_lock_prompt}</p>
                <p className="mt-2 text-xs font-semibold text-slate-500">
                  One actor only. Each reference changes pose or camera angle, not face, outfit, age, body type, or setting.
                </p>
              </div>
              <div className="grid gap-4 xl:grid-cols-2">
                {productionPackage.character_reference_prompts.map((prompt) => (
                  <div key={prompt.reference_id} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                    <div className="mb-3 flex items-start justify-between gap-3">
                      <div>
                        <p className="field-label">{prompt.reference_id}</p>
                        <h5 className="text-base font-black text-slate-950">{prompt.purpose}</h5>
                        <p className="mt-1 text-xs font-semibold text-teal-700">{prompt.aspect_ratio}</p>
                      </div>
                      <CopyButton
                        value={buildReferenceCopy(
                          prompt,
                          productionPackage.character_bible.identity_lock_prompt,
                          productionPackage.character_bible.base_prompt,
                        )}
                      />
                    </div>
                    <p className="text-sm leading-6 text-slate-700">{prompt.prompt}</p>
                    <p className="mt-3 text-xs font-black uppercase tracking-wide text-rose-700">Negative</p>
                    <p className="mt-1 text-sm leading-6 text-slate-600">{prompt.negative_prompt}</p>
                  </div>
                ))}
              </div>
            </WorkflowStep>

            <WorkflowStep number={2} title="Generate scene keyframes" tool="Use image generation. Upload the matching character reference and product/app assets, then paste one keyframe prompt per scene.">
              <div className="grid gap-4">
                {productionPackage.production_scenes.map((scene) => (
                  <div key={`keyframe-${scene.scene_number}`} className="rounded-lg border border-slate-200 bg-white p-4">
                    <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="field-label">Scene {scene.scene_number}</p>
                        <h5 className="text-base font-black text-slate-950">{scene.creative_objective}</h5>
                        <p className="mt-1 text-sm text-slate-500">
                          References: {formatList(scene.required_reference_assets)}
                        </p>
                      </div>
                      <CopyButton value={buildKeyframeCopy(scene)} />
                    </div>
                    <PromptBlock label="Keyframe prompt" value={scene.keyframe_prompt} />
                  </div>
                ))}
              </div>
            </WorkflowStep>

            <WorkflowStep number={3} title="Animate each scene" tool="Use an image-to-video or reference-to-video model. Feed the keyframe image, references, video prompt, motion, and consistency lock.">
              <div className="grid gap-4">
                {productionPackage.production_scenes.map((scene) => (
                  <div key={`video-${scene.scene_number}`} className="rounded-lg border border-slate-200 bg-white p-4">
                    <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="field-label">Scene {scene.scene_number}</p>
                        <h5 className="text-base font-black text-slate-950">
                          {scene.duration_seconds}s / {scene.generation_mode} / {scene.shot_type}
                        </h5>
                      </div>
                      <CopyButton value={buildVideoCopy(scene)} />
                    </div>
                    <div className="grid gap-3 lg:grid-cols-2">
                      <PromptBlock label="Video prompt" value={scene.video_prompt} />
                      <PromptBlock label="Motion + consistency" value={`${scene.motion_instruction}\n\n${scene.consistency_instruction}`} />
                    </div>
                  </div>
                ))}
              </div>
            </WorkflowStep>

            <WorkflowStep number={4} title="Add overlays and app UI" tool="Do this in the editor after video generation. Keep UI text readable instead of asking the video model to invent app screens.">
              <div className="grid gap-4">
                {productionPackage.production_scenes.map((scene) => (
                  <div key={`overlay-${scene.scene_number}`} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                    <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="field-label">Scene {scene.scene_number}</p>
                        <h5 className="text-base font-black text-slate-950">{scene.on_screen_text}</h5>
                      </div>
                      <CopyButton value={buildOverlayCopy(scene)} />
                    </div>
                    <OverlayList items={scene.ui_overlay_plan} />
                  </div>
                ))}
              </div>
              <div className="mt-4 rounded-lg border border-slate-200 bg-white p-4">
                <p className="field-label">App UI overlay notes</p>
                <p className="mt-2 text-sm leading-6 text-slate-700">{productionPackage.app_ui_overlay_notes}</p>
              </div>
            </WorkflowStep>

            <WorkflowStep number={5} title="Assemble final ad" tool="Use CapCut, Premiere, Runway editor, or your internal editor. Cut scenes in order, add subtitles, music, disclaimers, and export ratios.">
              <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
                <PromptBlock label="Edit plan" value={buildEditCopy(productionPackage.edit_plan)} />
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <p className="field-label">Production checklist</p>
                  <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-700">
                    {productionPackage.asset_checklist.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                  <p className="mt-4 field-label">Compliance</p>
                  <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-700">
                    {productionPackage.compliance_notes.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </WorkflowStep>

            <WorkflowStep number={6} title="Export package or call real video provider" tool="Export creates prompt files. Render Video only works after VIDEO_PROVIDER_NAME and VIDEO_PROVIDER_API_KEY are configured.">
              <div className="flex flex-wrap gap-3">
                <button className="btn-primary" type="button" disabled={disabled || exporting} onClick={() => void onExport()}>
                  {exporting ? "Exporting..." : "Export Production Package"}
                </button>
                <button className="btn-secondary" type="button" disabled={disabled || rendering} onClick={() => void onRender()}>
                  {rendering ? "Rendering..." : "Render Video"}
                </button>
              </div>
              {variant.export_package_url ? (
                <a
                  className="mt-4 block rounded-lg border border-teal-200 bg-teal-50 p-4 text-sm font-bold text-teal-800"
                  href={toApiUrl(variant.export_package_url)}
                  target="_blank"
                  rel="noreferrer"
                >
                  Download production_package.zip
                </a>
              ) : null}
              <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
                <p className="field-label">Render sequence</p>
                <ol className="mt-3 space-y-2 text-sm leading-6 text-slate-700">
                  {productionPackage.render_sequence.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ol>
              </div>
            </WorkflowStep>
          </>
        ) : null}
      </div>
    </article>
  );
}
