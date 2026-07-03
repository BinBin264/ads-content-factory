import { toApiUrl } from "../api/client";
import type { Variant } from "../types";

interface OutputPanelProps {
  variant: Variant;
}

function OutputLink({ label, path }: { label: string; path?: string | null }) {
  if (!path) {
    return (
      <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
        <p className="field-label">{label}</p>
        <p className="mt-1 text-sm text-slate-400">Not rendered yet</p>
      </div>
    );
  }

  return (
    <a className="block rounded-md border border-slate-200 bg-white p-3 transition hover:border-slate-400" href={toApiUrl(path)} target="_blank" rel="noreferrer">
      <p className="field-label">{label}</p>
      <p className="mt-1 break-all text-sm font-semibold text-slate-900">{path}</p>
    </a>
  );
}

export default function OutputPanel({ variant }: OutputPanelProps) {
  return (
    <div className="space-y-3">
      <div className="rounded-md bg-slate-100 px-3 py-2 text-sm">
        <span className="font-semibold text-slate-600">Status:</span>{" "}
        <span className={variant.video_status === "ready" ? "font-bold text-emerald-700" : "font-bold text-slate-700"}>{variant.video_status}</span>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        <OutputLink label="Mock video" path={variant.mock_video_url} />
        <OutputLink label="9:16 export" path={variant.export_9x16_url} />
        <OutputLink label="1:1 export" path={variant.export_1x1_url} />
      </div>
    </div>
  );
}
