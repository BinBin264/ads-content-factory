import { useState } from "react";
import OutputPanel from "./OutputPanel";
import StoryboardTable from "./StoryboardTable";
import type { Variant } from "../types";
import { buildKlingScenePrompt } from "../utils/kling";

type Tab = "overview" | "script" | "storyboard" | "prompts" | "caption" | "export";

interface VariantCardProps {
  variant: Variant;
}

const tabs: Array<{ id: Tab; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "script", label: "Script" },
  { id: "storyboard", label: "Storyboard" },
  { id: "prompts", label: "Scene Prompts" },
  { id: "caption", label: "Caption & Title" },
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

export default function VariantCard({ variant }: VariantCardProps) {
  const [activeTab, setActiveTab] = useState<Tab>("overview");
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
            <div>
              <dt className="field-label">Duration</dt>
              <dd className="mt-1 text-sm text-slate-800">{variant.duration}</dd>
            </div>
            <div>
              <dt className="field-label">Format</dt>
              <dd className="mt-1 text-sm text-slate-800">{variant.format}</dd>
            </div>
            <div>
              <dt className="field-label">Angle type</dt>
              <dd className="mt-1 text-sm text-slate-800">{variant.angle_type || "Not specified"}</dd>
            </div>
            <div>
              <dt className="field-label">Selected playbook</dt>
              <dd className="mt-1 text-sm text-slate-800">{variant.selected_playbook || "Not specified"}</dd>
            </div>
            <div className="md:col-span-2">
              <dt className="field-label">Hook</dt>
              <dd className="mt-1 text-sm text-slate-800">{variant.hook}</dd>
            </div>
            <div className="md:col-span-2">
              <dt className="field-label">CTA</dt>
              <dd className="mt-1 text-sm text-slate-800">{cta}</dd>
            </div>
          </dl>
        ) : null}

        {activeTab === "script" ? (
          <div className="space-y-4">
            <div>
              <div className="mb-2 flex items-center justify-between gap-3">
                <h4 className="text-sm font-bold text-slate-900">Full script</h4>
                <CopyButton value={variant.script} />
              </div>
              <pre className="whitespace-pre-wrap rounded-lg bg-slate-950 p-4 text-sm leading-6 text-slate-50 shadow-inner">{variant.script}</pre>
            </div>
            <div>
              <div className="mb-2 flex items-center justify-between gap-3">
                <h4 className="text-sm font-bold text-slate-900">Voiceover</h4>
                <CopyButton value={variant.voiceover} />
              </div>
              <p className="rounded-lg border border-teal-200 bg-teal-50 p-4 text-sm leading-6 text-slate-700">{variant.voiceover}</p>
            </div>
          </div>
        ) : null}

        {activeTab === "storyboard" ? <StoryboardTable scenes={variant.storyboard} /> : null}

        {activeTab === "prompts" ? (
          <div className="space-y-4">
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
              <p className="text-sm font-bold text-amber-950">Use this tab for manual Kling testing</p>
              <p className="mt-1 text-sm leading-6 text-amber-900">
                Upload the same character reference and app screenshot for every scene, then copy each Kling-ready prompt below into Kling one scene at a time.
              </p>
            </div>
            {variant.storyboard.map((scene) => (
              <div key={scene.scene_number} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <h4 className="rounded-md bg-slate-950 px-2 py-1 text-sm font-bold text-white">Scene {scene.scene_number}</h4>
                  <CopyButton value={buildKlingScenePrompt(variant, scene)} />
                </div>
                <p className="field-label">Kling-ready prompt</p>
                <pre className="mt-1 whitespace-pre-wrap rounded-lg bg-slate-950 p-4 text-sm leading-6 text-slate-50">
                  {buildKlingScenePrompt(variant, scene)}
                </pre>
                <details className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <summary className="cursor-pointer text-xs font-bold uppercase tracking-wide text-slate-500">Raw scene prompt</summary>
                  <p className="field-label mt-3">Generation prompt</p>
                  <p className="mt-1 text-sm leading-6 text-slate-700">{scene.generation_prompt}</p>
                  <p className="field-label mt-4">Negative prompt</p>
                  <p className="mt-1 text-sm leading-6 text-slate-700">{scene.negative_prompt}</p>
                </details>
              </div>
            ))}
          </div>
        ) : null}

        {activeTab === "caption" ? (
          <div className="space-y-4">
            <div className="rounded-lg border border-slate-200 p-4">
              <div className="mb-2 flex items-center justify-between gap-3">
                <p className="field-label">Title</p>
                <CopyButton value={variant.title} />
              </div>
              <p className="text-sm font-semibold text-slate-900">{variant.title}</p>
            </div>
            <div className="rounded-lg border border-slate-200 p-4">
              <div className="mb-2 flex items-center justify-between gap-3">
                <p className="field-label">Caption</p>
                <CopyButton value={variant.caption} />
              </div>
              <p className="text-sm leading-6 text-slate-700">{variant.caption}</p>
            </div>
            <div className="rounded-lg border border-slate-200 p-4">
              <div className="mb-2 flex items-center justify-between gap-3">
                <p className="field-label">Cover prompt</p>
                <CopyButton value={variant.cover_prompt} />
              </div>
              <p className="text-sm leading-6 text-slate-700">{variant.cover_prompt}</p>
            </div>
          </div>
        ) : null}

        {activeTab === "export" ? <OutputPanel variant={variant} /> : null}
      </div>
    </article>
  );
}
