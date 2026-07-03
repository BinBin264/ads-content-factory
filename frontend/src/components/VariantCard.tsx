import { useState } from "react";
import { toApiUrl } from "../api/client";
import type { ProductionScene, UIOverlayItem, Variant } from "../types";
import { formatList } from "../utils/format";
import StoryboardTable from "./StoryboardTable";

type Tab = "overview" | "script" | "storyboard" | "character" | "references" | "production" | "edit" | "export";

interface VariantCardProps {
  variant: Variant;
  onExport: () => Promise<void>;
  onRender: () => Promise<void>;
  exporting: boolean;
  rendering: boolean;
  disabled: boolean;
}

const tabs: Array<{ id: Tab; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "script", label: "Script" },
  { id: "storyboard", label: "Storyboard" },
  { id: "character", label: "Character" },
  { id: "references", label: "Reference Prompts" },
  { id: "production", label: "Production Scenes" },
  { id: "edit", label: "Overlay / Edit Plan" },
  { id: "export", label: "Export" },
];

async function copyText(value: string): Promise<void> {
  await navigator.clipboard.writeText(value);
}

function CopyButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    await copyText(value);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  };

  return (
    <button className="btn-secondary px-3 py-1 text-xs" type="button" onClick={copy}>
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

function EmptyPackage() {
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm font-semibold text-amber-900">
      Generate variants again to create a production package.
    </div>
  );
}

function TextBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="mb-2 flex items-center justify-between gap-3">
        <p className="field-label">{label}</p>
        <CopyButton value={value} />
      </div>
      <pre className="whitespace-pre-wrap rounded-lg bg-slate-950 p-4 text-sm leading-6 text-slate-50">{value}</pre>
    </div>
  );
}

function OverlayList({ items }: { items: UIOverlayItem[] }) {
  if (!items.length) {
    return <p className="text-sm text-slate-500">No overlay items planned for this scene.</p>;
  }

  return (
    <div className="grid gap-2">
      {items.map((item, index) => (
        <div key={`${item.overlay_type}-${index}`} className="rounded-md border border-slate-200 bg-slate-50 p-3">
          <p className="text-sm font-bold text-slate-900">
            {item.overlay_type}: {item.text}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {item.start_time}-{item.end_time} / {item.position}
          </p>
          <p className="mt-2 text-sm text-slate-700">{item.style_notes}</p>
          {item.safety_notes ? <p className="mt-1 text-xs font-semibold text-amber-700">{item.safety_notes}</p> : null}
        </div>
      ))}
    </div>
  );
}

function buildSceneCopy(scene: ProductionScene): string {
  return [
    `Scene ${scene.scene_number} (${scene.duration_seconds}s)`,
    `Objective: ${scene.creative_objective}`,
    `Generation mode: ${scene.generation_mode}`,
    `Required references: ${scene.required_reference_assets.join(", ")}`,
    "",
    "KEYFRAME PROMPT",
    scene.keyframe_prompt,
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
    "NEGATIVE",
    scene.negative_prompt,
  ].join("\n");
}

export default function VariantCard({ variant, onExport, onRender, exporting, rendering, disabled }: VariantCardProps) {
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const productionPackage = variant.production_package;
  const cta = variant.storyboard[variant.storyboard.length - 1]?.on_screen_text ?? "Not specified";

  return (
    <article className="card-accent overflow-hidden">
      <div className="border-b border-slate-200 bg-slate-50/70 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-base font-bold text-slate-950">{variant.name}</h3>
            <div className="mt-3 rounded-lg bg-slate-950 p-4 text-white">
              <div className="mb-2 flex items-center justify-between gap-3">
                <p className="text-xs font-bold uppercase tracking-wide text-slate-300">Hook</p>
                <CopyButton value={variant.hook} />
              </div>
              <p className="text-xl font-bold leading-snug">{variant.hook}</p>
            </div>
          </div>
          <span className="rounded-md border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-bold uppercase tracking-wide text-indigo-700">{variant.video_status}</span>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={`rounded-md px-3 py-2 text-sm font-semibold transition ${
                activeTab === tab.id ? "bg-teal-600 text-white shadow-sm" : "bg-white text-slate-600 hover:bg-teal-50"
              }`}
              type="button"
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="p-5">
        {activeTab === "overview" ? (
          <dl className="grid gap-4 md:grid-cols-2">
            <div className="rounded-lg border border-slate-200 bg-white p-3">
              <dt className="field-label">Duration</dt>
              <dd className="mt-1 text-sm text-slate-800">{variant.duration}</dd>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-3">
              <dt className="field-label">Format</dt>
              <dd className="mt-1 text-sm text-slate-800">{variant.format}</dd>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-3">
              <dt className="field-label">Angle type</dt>
              <dd className="mt-1 text-sm text-slate-800">{variant.angle_type || "Not specified"}</dd>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-3">
              <dt className="field-label">Selected playbook</dt>
              <dd className="mt-1 text-sm text-slate-800">{variant.selected_playbook || "Not specified"}</dd>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-3 md:col-span-2">
              <dt className="field-label">Hook</dt>
              <dd className="mt-1 text-sm text-slate-800">{variant.hook}</dd>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-3 md:col-span-2">
              <dt className="field-label">CTA</dt>
              <dd className="mt-1 text-sm text-slate-800">{cta}</dd>
            </div>
            {productionPackage ? (
              <div className="rounded-lg border border-teal-200 bg-teal-50 p-3 md:col-span-2">
                <dt className="field-label text-teal-700">Production package</dt>
                <dd className="mt-2 text-sm leading-6 text-slate-800">
                  {productionPackage.character_reference_prompts.length} reference prompts / {productionPackage.production_scenes.length} production scenes /{" "}
                  {formatList(productionPackage.edit_plan.export_ratios)} exports
                </dd>
              </div>
            ) : null}
          </dl>
        ) : null}

        {activeTab === "script" ? (
          <div className="space-y-4">
            <TextBlock label="Full script" value={variant.script} />
            <TextBlock label="Voiceover" value={variant.voiceover} />
          </div>
        ) : null}

        {activeTab === "storyboard" ? <StoryboardTable scenes={variant.storyboard} /> : null}

        {activeTab === "character" ? (
          productionPackage ? (
            <div className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-lg border border-teal-200 bg-teal-50 p-4">
                  <p className="field-label text-teal-700">Character Plan</p>
                  <h4 className="mt-2 text-lg font-black text-slate-950">{productionPackage.character_plan.recommended_character_type}</h4>
                  <p className="mt-2 text-sm leading-6 text-slate-700">{productionPackage.character_plan.reason}</p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-white p-4">
                  <p className="field-label">Character Bible</p>
                  <h4 className="mt-2 text-lg font-black text-slate-950">{productionPackage.character_bible.display_name}</h4>
                  <p className="mt-2 text-sm leading-6 text-slate-700">{productionPackage.character_bible.base_prompt}</p>
                </div>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                {[
                  ["Gender", productionPackage.character_bible.gender],
                  ["Age range", productionPackage.character_bible.age_range],
                  ["Face details", productionPackage.character_bible.face_details],
                  ["Hair", productionPackage.character_bible.hair],
                  ["Facial hair", productionPackage.character_bible.facial_hair],
                  ["Body type", productionPackage.character_bible.body_type],
                  ["Outfit", productionPackage.character_bible.outfit],
                  ["Setting", productionPackage.character_bible.setting],
                  ["Props", formatList(productionPackage.character_bible.props)],
                  ["Personality", formatList(productionPackage.character_bible.personality)],
                ].map(([label, value]) => (
                  <div key={label} className="rounded-lg border border-slate-200 bg-white p-3">
                    <p className="field-label">{label}</p>
                    <p className="mt-1 text-sm text-slate-800">{value}</p>
                  </div>
                ))}
              </div>
              <TextBlock label="Identity lock prompt" value={productionPackage.character_bible.identity_lock_prompt} />
              <TextBlock label="Consistency locks" value={productionPackage.character_bible.consistency_locks.join("\n")} />
              <TextBlock label="Negative identity changes" value={productionPackage.character_bible.negative_identity_changes.join("\n")} />
            </div>
          ) : (
            <EmptyPackage />
          )
        ) : null}

        {activeTab === "references" ? (
          productionPackage ? (
            <div className="grid gap-4 xl:grid-cols-2">
              {productionPackage.character_reference_prompts.map((prompt) => (
                <div key={prompt.reference_id} className="rounded-lg border border-slate-200 bg-white p-4">
                  <div className="mb-3 flex items-start justify-between gap-3">
                    <div>
                      <p className="field-label">{prompt.reference_id}</p>
                      <h4 className="text-base font-black text-slate-950">{prompt.purpose}</h4>
                      <p className="mt-1 text-xs font-semibold text-teal-700">{prompt.aspect_ratio}</p>
                    </div>
                    <CopyButton value={`${prompt.prompt}\n\nNegative prompt:\n${prompt.negative_prompt}`} />
                  </div>
                  <p className="text-sm leading-6 text-slate-700">{prompt.prompt}</p>
                  <p className="mt-3 text-xs font-bold uppercase tracking-wide text-rose-700">Negative</p>
                  <p className="mt-1 text-sm leading-6 text-slate-600">{prompt.negative_prompt}</p>
                  {prompt.notes ? <p className="mt-3 text-xs text-slate-500">{prompt.notes}</p> : null}
                </div>
              ))}
            </div>
          ) : (
            <EmptyPackage />
          )
        ) : null}

        {activeTab === "production" ? (
          productionPackage ? (
            <div className="space-y-5">
              {productionPackage.production_scenes.map((scene) => (
                <div key={scene.scene_number} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
                  <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="inline-flex rounded-md bg-slate-950 px-2 py-1 text-sm font-bold text-white">Scene {scene.scene_number}</p>
                      <h4 className="mt-2 text-lg font-black text-slate-950">{scene.creative_objective}</h4>
                      <p className="mt-1 text-sm text-slate-500">
                        {scene.duration_seconds}s / {scene.generation_mode} / {scene.shot_type}
                      </p>
                    </div>
                    <CopyButton value={buildSceneCopy(scene)} />
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    <div className="rounded-lg bg-slate-50 p-3">
                      <p className="field-label">Visual description</p>
                      <p className="mt-1 text-sm leading-6 text-slate-700">{scene.visual_description}</p>
                    </div>
                    <div className="rounded-lg bg-slate-50 p-3">
                      <p className="field-label">Action description</p>
                      <p className="mt-1 text-sm leading-6 text-slate-700">{scene.action_description}</p>
                    </div>
                    <div className="rounded-lg bg-slate-50 p-3">
                      <p className="field-label">Camera angle</p>
                      <p className="mt-1 text-sm leading-6 text-slate-700">{scene.camera_angle}</p>
                    </div>
                    <div className="rounded-lg bg-slate-50 p-3">
                      <p className="field-label">Required reference assets</p>
                      <p className="mt-1 text-sm leading-6 text-slate-700">{formatList(scene.required_reference_assets)}</p>
                    </div>
                  </div>
                  <div className="mt-4 grid gap-4">
                    <TextBlock label="Keyframe prompt" value={scene.keyframe_prompt} />
                    <TextBlock label="Video prompt" value={scene.video_prompt} />
                    <TextBlock label="Motion instruction" value={scene.motion_instruction} />
                    <TextBlock label="Consistency instruction" value={scene.consistency_instruction} />
                    <TextBlock label="Negative prompt" value={scene.negative_prompt} />
                  </div>
                  <div className="mt-4 rounded-lg border border-slate-200 bg-white p-3">
                    <p className="field-label">UI overlay plan</p>
                    <div className="mt-2">
                      <OverlayList items={scene.ui_overlay_plan} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyPackage />
          )
        ) : null}

        {activeTab === "edit" ? (
          productionPackage ? (
            <div className="space-y-4">
              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <p className="field-label">App UI overlay notes</p>
                <p className="mt-2 text-sm leading-6 text-slate-700">{productionPackage.app_ui_overlay_notes}</p>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-lg border border-slate-200 bg-white p-4">
                  <p className="field-label">Edit plan</p>
                  <p className="mt-2 text-sm leading-6 text-slate-700">{productionPackage.edit_plan.pacing_notes}</p>
                  <p className="mt-3 text-sm text-slate-700">
                    <span className="font-bold">Music:</span> {productionPackage.edit_plan.music_direction}
                  </p>
                  <p className="mt-2 text-sm text-slate-700">
                    <span className="font-bold">Subtitles:</span> {productionPackage.edit_plan.subtitle_style}
                  </p>
                  <p className="mt-2 text-sm text-slate-700">
                    <span className="font-bold">Export ratios:</span> {formatList(productionPackage.edit_plan.export_ratios)}
                  </p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-white p-4">
                  <p className="field-label">Required post-production steps</p>
                  <ul className="mt-2 space-y-2 text-sm leading-6 text-slate-700">
                    {productionPackage.edit_plan.required_post_production_steps.map((step) => (
                      <li key={step}>{step}</li>
                    ))}
                  </ul>
                </div>
              </div>
              <TextBlock label="Cut sequence" value={productionPackage.edit_plan.cut_sequence.join("\n")} />
              <TextBlock label="Render sequence" value={productionPackage.render_sequence.join("\n")} />
              <TextBlock label="Asset checklist" value={productionPackage.asset_checklist.join("\n")} />
              <TextBlock label="Compliance notes" value={productionPackage.compliance_notes.join("\n")} />
            </div>
          ) : (
            <EmptyPackage />
          )
        ) : null}

        {activeTab === "export" ? (
          <div className="space-y-4">
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm font-bold text-slate-900">Status: {variant.video_status}</p>
              <p className="mt-1 text-sm text-slate-600">
                Export writes prompt and plan files. Render Video only calls a configured video provider.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <button className="btn-primary" type="button" disabled={disabled || exporting || !productionPackage} onClick={() => void onExport()}>
                {exporting ? "Exporting..." : "Export Production Package"}
              </button>
              <button className="btn-secondary" type="button" disabled={disabled || rendering || !productionPackage} onClick={() => void onRender()}>
                {rendering ? "Rendering..." : "Render Video"}
              </button>
            </div>
            {variant.export_package_url ? (
              <a className="block rounded-lg border border-teal-200 bg-teal-50 p-4 text-sm font-bold text-teal-800" href={toApiUrl(variant.export_package_url)} target="_blank" rel="noreferrer">
                Download production_package.zip
              </a>
            ) : null}
            {!productionPackage ? <EmptyPackage /> : null}
          </div>
        ) : null}
      </div>
    </article>
  );
}
