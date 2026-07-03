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
    <article className={`rounded-lg border p-4 ${selected ? "border-slate-900 bg-slate-50" : "border-slate-200 bg-white"}`}>
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold text-slate-950">{angle.name}</h3>
          <span className={`mt-2 inline-flex rounded-full border px-2 py-1 text-xs font-bold ${badgeClass}`}>{angle.angle_type}</span>
        </div>
        <label className="flex items-center gap-2 text-xs font-semibold text-slate-600">
          <input type="checkbox" checked={selected} onChange={() => onToggle(angle.id)} className="h-4 w-4 rounded border-slate-300" />
          Select
        </label>
      </div>

      <p className="rounded-md bg-slate-100 px-3 py-2 text-sm font-semibold text-slate-900">{angle.hook}</p>

      <dl className="mt-4 grid gap-3 text-sm md:grid-cols-2">
        <div>
          <dt className="field-label">Audience</dt>
          <dd className="mt-1 text-slate-700">{angle.target_audience}</dd>
        </div>
        <div>
          <dt className="field-label">Score</dt>
          <dd className="mt-1 font-bold text-slate-900">{angle.score}</dd>
        </div>
        <div>
          <dt className="field-label">Pain point</dt>
          <dd className="mt-1 text-slate-700">{angle.pain_point}</dd>
        </div>
        <div>
          <dt className="field-label">Trigger</dt>
          <dd className="mt-1 text-slate-700">{angle.emotional_trigger}</dd>
        </div>
        <div>
          <dt className="field-label">Product role</dt>
          <dd className="mt-1 text-slate-700">{angle.product_role}</dd>
        </div>
        <div>
          <dt className="field-label">Proof moment</dt>
          <dd className="mt-1 text-slate-700">{angle.proof_demo_moment}</dd>
        </div>
        <div>
          <dt className="field-label">CTA</dt>
          <dd className="mt-1 text-slate-700">{angle.cta}</dd>
        </div>
        <div>
          <dt className="field-label">Why it can work</dt>
          <dd className="mt-1 text-slate-700">{angle.reason_why_it_can_work}</dd>
        </div>
      </dl>
    </article>
  );
}
