import type { KeyframePrompt, PlanCreation, StorytellingScene } from "../types";

interface PlanCreationCardProps {
  planCreation?: PlanCreation | null;
}

function copyText(value: string): Promise<void> {
  return navigator.clipboard.writeText(value);
}

function TextList({ items }: { items?: string[] }) {
  if (!items?.length) {
    return <p className="mt-2 text-sm text-slate-500">Not specified</p>;
  }

  return (
    <ul className="mt-2 space-y-1 text-sm leading-6 text-slate-700">
      {items.map((item) => (
        <li key={item}>- {item}</li>
      ))}
    </ul>
  );
}

function CopyBlock({ label, value, tone = "dark" }: { label: string; value?: string; tone?: "dark" | "light" }) {
  if (!value) {
    return null;
  }

  const isDark = tone === "dark";

  return (
    <div className={`rounded-lg border p-4 ${isDark ? "border-slate-800 bg-slate-950 text-white" : "border-slate-200 bg-slate-50 text-slate-900"}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className={`text-xs font-black uppercase tracking-wide ${isDark ? "text-teal-200" : "text-slate-500"}`}>{label}</p>
        <button
          className={`rounded-md px-3 py-1.5 text-xs font-bold transition ${
            isDark ? "bg-white/10 text-white hover:bg-white/15" : "border border-slate-200 bg-white text-slate-700 hover:border-teal-300 hover:text-teal-700"
          }`}
          onClick={() => void copyText(value)}
          type="button"
        >
          Copy
        </button>
      </div>
      <p className={`mt-3 whitespace-pre-wrap text-sm leading-7 ${isDark ? "text-slate-100" : "text-slate-700"}`}>{value}</p>
    </div>
  );
}

function KeyframePromptCard({ prompt, index }: { prompt: KeyframePrompt; index: number }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-black uppercase tracking-wide text-slate-400">Keyframe {index + 1} / {prompt.timing}</p>
          <p className="mt-1 text-sm font-black text-slate-950">{prompt.label}</p>
        </div>
        {prompt.productReferenceIds.length ? (
          <span className="rounded-md border border-teal-200 bg-teal-50 px-2 py-1 text-xs font-bold text-teal-700">
            Uses {prompt.productReferenceIds.join(", ")}
          </span>
        ) : null}
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-500">{prompt.purpose}</p>
      <CopyBlock label="Image/keyframe prompt" value={prompt.prompt} tone="light" />
    </div>
  );
}

function SceneWorkflowCard({ scene }: { scene: StorytellingScene }) {
  const displayDuration = scene.durationSec || 4;

  return (
    <article className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-black uppercase tracking-wide text-rose-600">Scene {scene.sceneIndex} / {displayDuration}s clip</p>
          <h5 className="mt-1 text-xl font-black text-slate-950">{scene.title}</h5>
          <p className="mt-2 text-sm leading-6 text-slate-600">{scene.sceneGoal}</p>
        </div>
        <span className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-black uppercase tracking-wide text-amber-700">
          {scene.narrativePurpose}
        </span>
      </div>

      <div className="mt-5 grid gap-3 lg:grid-cols-3">
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs font-black uppercase tracking-wide text-slate-400">1. Understand action</p>
          <p className="mt-2 text-sm font-semibold leading-6 text-slate-900">{scene.visualAction}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs font-black uppercase tracking-wide text-slate-400">2. Product moment</p>
          <p className="mt-2 text-sm leading-6 text-slate-700">{scene.productMoment}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs font-black uppercase tracking-wide text-slate-400">3. Camera</p>
          <p className="mt-2 text-sm font-semibold text-slate-900">{scene.camera?.selected}</p>
          <p className="mt-1 text-sm leading-6 text-slate-700">{scene.camera?.movement}</p>
        </div>
      </div>

      <div className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-4">
        <p className="text-xs font-black uppercase tracking-wide text-slate-400">Create or pick keyframe images for this 4s clip</p>
        <div className="mt-3 space-y-3">
          {scene.keyframePrompts?.map((prompt, index) => (
            <KeyframePromptCard key={prompt.id} prompt={prompt} index={index} />
          ))}
        </div>
      </div>

      <div className="mt-5 grid gap-3 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs font-black uppercase tracking-wide text-slate-400">Voice / overlay</p>
          <div className="mt-3 space-y-2">
            {scene.voiceLines?.map((line) => (
              <div key={`${line.timing}-${line.line}`} className="rounded-md border border-slate-200 bg-white p-3">
                <p className="text-xs font-bold uppercase tracking-wide text-slate-400">{line.timing} / {line.emotion}</p>
                <p className="mt-1 text-sm font-semibold leading-6 text-slate-900">{line.line}</p>
              </div>
            ))}
          </div>
          <p className="mt-3 text-sm text-slate-600">Overlay: {scene.onScreenText || "No overlay text"}</p>
        </div>
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-4">
          <p className="text-xs font-black uppercase tracking-wide text-rose-700">Avoid while generating</p>
          <TextList items={scene.negativeRules} />
        </div>
      </div>

      <div className="mt-5">
        <CopyBlock label="Copy this final 4s video prompt to Flow/Kling/video model" value={scene.finalVideoPrompt} />
      </div>
    </article>
  );
}

export default function PlanCreationCard({ planCreation }: PlanCreationCardProps) {
  if (!planCreation) {
    return <div className="empty-state">Plan Creation output will appear after generation.</div>;
  }

  const hasPromptOutput = Boolean(planCreation.productAnalysis || planCreation.scenes?.length);

  if (!hasPromptOutput) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-5">
        <p className="text-sm font-black text-slate-950">{planCreation.main_message}</p>
        <p className="mt-2 text-sm leading-7 text-slate-700">{planCreation.product_truth}</p>
        <p className="mt-3 text-xs text-slate-500">
          Legacy plan detected. Regenerate Plan Creation to get the step-by-step output.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {planCreation.scenes?.map((scene) => (
        <SceneWorkflowCard key={scene.sceneIndex} scene={scene} />
      ))}
    </div>
  );
}
