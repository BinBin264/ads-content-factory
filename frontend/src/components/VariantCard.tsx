import { useMemo, useState } from "react";
import { toApiUrl } from "../api/client";
import type { PipelineAsset, PipelineStep, Variant } from "../types";

interface VariantCardProps {
  variant: Variant;
  onExport: () => Promise<void>;
  onRender: () => Promise<void>;
  onRunPipeline: () => Promise<void>;
  onRunStep: (stepId: string) => Promise<void>;
  onUploadStepResult: (stepId: string, file: File, assetKey?: string) => Promise<void>;
  exporting: boolean;
  rendering: boolean;
  runningPipeline: boolean;
  runningStep: boolean;
  uploadingStep: boolean;
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
    <button className="btn-secondary px-3 py-1 text-xs" type="button" onClick={copy} disabled={!value}>
      {copied ? "Copied" : label}
    </button>
  );
}

function PromptBlock({ label, value }: { label: string; value?: string | null }) {
  if (!value) {
    return null;
  }

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

function statusClass(status: PipelineStep["status"]): string {
  if (status === "completed") {
    return "border-emerald-200 bg-emerald-50 text-emerald-800";
  }
  if (status === "ready") {
    return "border-teal-200 bg-teal-50 text-teal-800";
  }
  if (status === "running") {
    return "border-amber-200 bg-amber-50 text-amber-800";
  }
  if (status === "failed") {
    return "border-rose-200 bg-rose-50 text-rose-800";
  }
  return "border-slate-200 bg-slate-50 text-slate-500";
}

function assetMap(assets: PipelineAsset[], steps: PipelineStep[]): Map<string, PipelineAsset> {
  const map = new Map<string, PipelineAsset>();
  assets.forEach((asset) => map.set(asset.asset_key, asset));
  steps.forEach((step) => step.output_assets.forEach((asset) => map.set(asset.asset_key, asset)));
  return map;
}

function AssetLink({ asset }: { asset: PipelineAsset }) {
  const label = `${asset.asset_key} (${asset.asset_type})`;
  if (!asset.url) {
    return <span className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-semibold text-slate-700">{label}</span>;
  }

  return (
    <a
      className="rounded-md border border-teal-200 bg-teal-50 px-2 py-1 text-xs font-bold text-teal-800 hover:bg-teal-100"
      href={toApiUrl(asset.url)}
      target="_blank"
      rel="noreferrer"
    >
      {label}
    </a>
  );
}

function valueToString(value: unknown): string {
  if (Array.isArray(value)) {
    return value.map((item) => String(item)).join(", ");
  }
  if (value === null || value === undefined) {
    return "";
  }
  return String(value);
}

function WorkflowList({ label, items }: { label: string; items: string[] }) {
  if (!items.length) {
    return null;
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <p className="field-label">{label}</p>
      <ul className="mt-2 space-y-2 text-sm leading-6 text-slate-700">
        {items.map((item) => (
          <li key={item} className="flex gap-2">
            <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-slate-400" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ProviderOption({ option }: { option: Record<string, unknown> }) {
  const status = valueToString(option.status);
  const configured = Boolean(option.configured);
  const recommended = Array.isArray(option.recommended_manual_tools) ? option.recommended_manual_tools.map((item) => String(item)) : [];

  return (
    <div className="rounded-md border border-slate-200 bg-white p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-bold text-slate-900">{valueToString(option.provider_name) || "manual_web_tool"}</p>
        <span className={`rounded-md px-2 py-1 text-xs font-black ${configured ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-600"}`}>
          {status || (configured ? "configured" : "manual")}
        </span>
      </div>
      <p className="mt-1 text-xs leading-5 text-slate-500">{valueToString(option.notes)}</p>
      {recommended.length ? <p className="mt-2 text-xs text-slate-500">Manual tools: {recommended.join(", ")}</p> : null}
    </div>
  );
}

function StepCard({
  step,
  assets,
  disabled,
  runningStep,
  uploadingStep,
  onRunStep,
  onUploadStepResult,
}: {
  step: PipelineStep;
  assets: Map<string, PipelineAsset>;
  disabled: boolean;
  runningStep: boolean;
  uploadingStep: boolean;
  onRunStep: (stepId: string) => Promise<void>;
  onUploadStepResult: (stepId: string, file: File, assetKey?: string) => Promise<void>;
}) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const defaultOutputKey = step.expected_outputs[0]?.asset_key;
  const canRun = !disabled && !runningStep && ["ready", "failed"].includes(step.status);
  const canUpload = !disabled && !uploadingStep && Boolean(selectedFile);

  const upload = async () => {
    if (!selectedFile) {
      return;
    }
    await onUploadStepResult(step.step_id, selectedFile, defaultOutputKey);
    setSelectedFile(null);
  };

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="grid h-8 w-8 place-items-center rounded-md bg-slate-950 text-xs font-black text-white">{step.step_number}</span>
            <span className={`rounded-md border px-2 py-1 text-xs font-black uppercase tracking-wide ${statusClass(step.status)}`}>
              {step.status}
            </span>
            <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-bold text-slate-600">{step.stage_label || step.stage}</span>
            <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-bold text-slate-600">{step.tool_type}</span>
          </div>
          <h4 className="mt-3 text-lg font-black text-slate-950">{step.title}</h4>
          <p className="mt-2 text-sm leading-6 text-slate-700">{step.goal}</p>
          {step.stage_purpose ? <p className="mt-2 text-xs leading-5 text-slate-500">{step.stage_purpose}</p> : null}
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="btn-secondary px-3 py-2 text-xs" type="button" disabled={!canRun} onClick={() => void onRunStep(step.step_id)}>
            {runningStep ? "Running..." : "Run Step"}
          </button>
        </div>
      </div>

      {step.error_message ? <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm font-semibold text-rose-800">{step.error_message}</div> : null}

      <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-4">
          <WorkflowList label="Source artifacts from previous phases" items={step.source_artifacts} />

          {step.required_inputs.length ? (
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p className="field-label">Required inputs</p>
              <div className="mt-3 grid gap-2">
                {step.required_inputs.map((input) => {
                  const asset = assets.get(input.asset_key);
                  return (
                    <div key={input.asset_key} className="rounded-md border border-slate-200 bg-white p-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-sm font-bold text-slate-900">{input.label}</p>
                        <span className={`rounded-md px-2 py-1 text-xs font-black ${asset ? "bg-emerald-100 text-emerald-800" : input.required ? "bg-rose-100 text-rose-800" : "bg-slate-100 text-slate-600"}`}>
                          {asset ? "available" : input.required ? "missing" : "optional"}
                        </span>
                      </div>
                      <p className="mt-1 text-xs leading-5 text-slate-500">{input.instructions}</p>
                      {asset ? (
                        <div className="mt-2">
                          <AssetLink asset={asset} />
                        </div>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            </div>
          ) : null}

          <PromptBlock label="Prompt to copy" value={step.prompt_to_copy} />
          <PromptBlock label="Negative prompt" value={step.negative_prompt_to_copy} />
          <PromptBlock label="Motion instruction" value={step.motion_instruction} />
          <PromptBlock label="Consistency instruction" value={step.consistency_instruction} />

          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="field-label">Manual instructions</p>
            <ul className="mt-2 space-y-2 text-sm leading-6 text-slate-700">
              {step.manual_instructions.map((instruction) => (
                <li key={instruction}>{instruction}</li>
              ))}
            </ul>
          </div>
        </div>

        <aside className="space-y-4">
          {step.provider_options.length ? (
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p className="field-label">Provider or manual path</p>
              <div className="mt-2 space-y-2">
                {step.provider_options.map((option, index) => (
                  <ProviderOption key={`${step.step_id}-provider-${index}`} option={option} />
                ))}
              </div>
            </div>
          ) : null}

          <WorkflowList label="Review focus" items={step.review_focus} />
          <WorkflowList label="Success criteria" items={step.success_criteria} />

          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="field-label">Settings</p>
            <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap rounded-md bg-white p-3 text-xs leading-5 text-slate-700">
              {JSON.stringify(step.settings, null, 2)}
            </pre>
          </div>

          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="field-label">Expected outputs</p>
            <div className="mt-2 space-y-2">
              {step.expected_outputs.map((output) => (
                <div key={output.asset_key} className="rounded-md border border-slate-200 bg-white p-2">
                  <p className="text-sm font-bold text-slate-900">{output.label}</p>
                  <p className="mt-1 text-xs text-slate-500">{output.asset_key} / {output.file_name_hint}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="field-label">Upload result</p>
            <input
              className="mt-2 block w-full text-sm text-slate-700"
              type="file"
              disabled={disabled || uploadingStep}
              onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
            />
            <button className="btn-primary mt-3 w-full" type="button" disabled={!canUpload} onClick={() => void upload()}>
              {uploadingStep ? "Uploading..." : "Upload Step Output"}
            </button>
            {defaultOutputKey ? <p className="mt-2 text-xs text-slate-500">Asset key: {defaultOutputKey}</p> : null}
          </div>

          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="field-label">Output assets</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {step.output_assets.length ? step.output_assets.map((asset) => <AssetLink key={asset.asset_id} asset={asset} />) : <span className="text-sm text-slate-500">No output yet.</span>}
            </div>
          </div>
        </aside>
      </div>
    </article>
  );
}

export default function VariantCard({
  variant,
  onExport,
  onRender,
  onRunPipeline,
  onRunStep,
  onUploadStepResult,
  exporting,
  rendering,
  runningPipeline,
  runningStep,
  uploadingStep,
  disabled,
}: VariantCardProps) {
  const pipeline = variant.generation_pipeline;
  const assets = useMemo(() => (pipeline ? assetMap(pipeline.assets, pipeline.steps) : new Map<string, PipelineAsset>()), [pipeline]);
  const sourceArtifacts = pipeline?.source_artifacts ?? [];
  const providerContracts = pipeline?.provider_contracts ?? [];

  return (
    <article className="card-accent overflow-hidden">
      <div className="border-b border-slate-200 bg-slate-950 p-5 text-white">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-4xl">
            <p className="text-xs font-black uppercase tracking-wide text-teal-300">Executable generation pipeline</p>
            <h3 className="mt-2 text-xl font-black">{variant.name}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-300">{variant.hook}</p>
          </div>
          <span className="rounded-md border border-white/15 bg-white/10 px-3 py-1 text-xs font-bold uppercase tracking-wide text-white">
            {pipeline?.status ?? variant.video_status}
          </span>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <button className="btn-primary" type="button" disabled={disabled || runningPipeline || !pipeline} onClick={() => void onRunPipeline()}>
            {runningPipeline ? "Running..." : "Run Full Pipeline"}
          </button>
          <button className="btn-secondary" type="button" disabled={disabled || rendering || !pipeline} onClick={() => void onRender()}>
            {rendering ? "Rendering..." : "Render Video"}
          </button>
          <button className="btn-secondary" type="button" disabled={disabled || exporting || !pipeline} onClick={() => void onExport()}>
            {exporting ? "Exporting..." : "Export Production Package"}
          </button>
          {variant.export_package_url ? (
            <a className="btn-secondary" href={toApiUrl(variant.export_package_url)} target="_blank" rel="noreferrer">
              Download Package
            </a>
          ) : null}
        </div>
      </div>

      <div className="space-y-5 p-5">
        {!pipeline ? (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm font-semibold text-amber-900">
            Regenerate Video Workflow to create executable pipeline steps.
          </div>
        ) : (
          <>
            <div className="grid gap-3 md:grid-cols-4">
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="field-label">Steps</p>
                <p className="mt-1 text-2xl font-black text-slate-950">{pipeline.steps.length}</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="field-label">Assets</p>
                <p className="mt-1 text-2xl font-black text-slate-950">{assets.size}</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="field-label">Completed</p>
                <p className="mt-1 text-2xl font-black text-emerald-700">{pipeline.steps.filter((step) => step.status === "completed").length}</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="field-label">Ready</p>
                <p className="mt-1 text-2xl font-black text-teal-700">{pipeline.steps.filter((step) => step.status === "ready").length}</p>
              </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <p className="field-label">Workflow contract</p>
                <h4 className="mt-2 text-lg font-black text-slate-950">{pipeline.pipeline_name} v{pipeline.pipeline_version}</h4>
                <p className="mt-2 text-sm leading-6 text-slate-600">{pipeline.objective}</p>
                <div className="mt-4 grid gap-2 md:grid-cols-2">
                  {sourceArtifacts.map((artifact, index) => (
                    <div key={`${valueToString(artifact.artifact_key)}-${index}`} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                      <p className="text-sm font-bold text-slate-900">{valueToString(artifact.label)}</p>
                      <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-slate-400">{valueToString(artifact.source_phase)}</p>
                      <p className="mt-2 text-xs leading-5 text-slate-500">{valueToString(artifact.description)}</p>
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <p className="field-label">Provider registry</p>
                <div className="mt-3 space-y-2">
                  {providerContracts.map((contract, index) => (
                    <ProviderOption key={`${valueToString(contract.tool_type)}-${index}`} option={contract} />
                  ))}
                </div>
              </div>
            </div>

            {pipeline.steps.map((step) => (
              <StepCard
                key={step.step_id}
                step={step}
                assets={assets}
                disabled={disabled}
                runningStep={runningStep}
                uploadingStep={uploadingStep}
                onRunStep={onRunStep}
                onUploadStepResult={onUploadStepResult}
              />
            ))}
          </>
        )}
      </div>
    </article>
  );
}
