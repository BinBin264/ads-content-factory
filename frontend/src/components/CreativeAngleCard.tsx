import type { CreativeAngle } from "../types";

interface CreativeAngleCardProps {
  angle: CreativeAngle;
  selected: boolean;
  onToggle: (angleId: string) => void;
}

const angleTypeClass: Record<string, string> = {
  storytelling: "bg-rose-50 text-rose-700 border-rose-200",
  product_demo: "bg-blue-50 text-blue-700 border-blue-200",
  problem_solution: "bg-amber-50 text-amber-700 border-amber-200",
  curiosity: "bg-violet-50 text-violet-700 border-violet-200",
  social_proof: "bg-emerald-50 text-emerald-700 border-emerald-200",
};

export default function CreativeAngleCard({ angle, selected, onToggle }: CreativeAngleCardProps) {
  const badgeClass = angleTypeClass[angle.angle_type] ?? "bg-slate-100 text-slate-600 border-slate-200";

  return (
    <article className={`overflow-hidden rounded-lg border shadow-sm transition hover:-translate-y-0.5 hover:shadow-soft ${selected ? "border-teal-400 bg-teal-50/60" : "border-slate-200 bg-white"}`}>
      <div className="border-b border-slate-200 bg-slate-50/70 p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-bold text-slate-950">{angle.name}</h3>
              <span className={`inline-flex rounded-full border px-2 py-1 text-xs font-bold ${badgeClass}`}>{angle.angle_type}</span>
            </div>
            <p className="mt-3 rounded-md bg-slate-950 px-3 py-3 text-sm font-bold leading-6 text-white">{angle.hook}</p>
          </div>
          <label className="flex shrink-0 items-center gap-2 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-bold text-slate-600">
            <input type="checkbox" checked={selected} onChange={() => onToggle(angle.id)} className="h-4 w-4 rounded border-slate-300 accent-teal-600" />
            Select
          </label>
        </div>
      </div>

      <div className="space-y-4 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2">
            <span className="text-xs font-bold uppercase tracking-wide text-amber-700">Score </span>
            <span className="text-lg font-black text-amber-900">{Math.round(angle.score)}</span>
          </div>
          <p className="text-xs font-semibold text-slate-500">{angle.target_audience}</p>
        </div>

        <dl className="grid gap-4 text-sm md:grid-cols-2">
        <div>
          <dt className="field-label">Pain point</dt>
          <dd className="mt-1 text-slate-700">{angle.pain_point}</dd>
        </div>
        <div>
          <dt className="field-label">Proof moment</dt>
          <dd className="mt-1 text-slate-700">{angle.proof_demo_moment}</dd>
        </div>
        <div className="md:col-span-2">
          <dt className="field-label">Why it can work</dt>
          <dd className="mt-1 text-slate-700">{angle.reason_why_it_can_work}</dd>
        </div>
      </dl>

        <details className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
          <summary className="cursor-pointer text-xs font-bold uppercase tracking-wide text-slate-500">Details</summary>
          <dl className="mt-3 grid gap-3 text-sm md:grid-cols-2">
            <div>
              <dt className="field-label">Trigger</dt>
              <dd className="mt-1 text-slate-700">{angle.emotional_trigger}</dd>
            </div>
            <div>
              <dt className="field-label">CTA</dt>
              <dd className="mt-1 text-slate-700">{angle.cta}</dd>
            </div>
            <div className="md:col-span-2">
              <dt className="field-label">Product role</dt>
              <dd className="mt-1 text-slate-700">{angle.product_role}</dd>
            </div>
          </dl>
        </details>
      </div>
    </article>
  );
}
