import type { CreativePlan } from "../types";
import { formatList } from "../utils/format";

interface CreativePlanCardProps {
  creativePlan?: CreativePlan | null;
}

function InfoBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <p className="field-label">{label}</p>
      <p className="mt-2 text-sm leading-7 text-slate-800">{value || "Not specified"}</p>
    </div>
  );
}

export default function CreativePlanCard({ creativePlan }: CreativePlanCardProps) {
  if (!creativePlan) {
    return <div className="empty-state">Creative Plan will appear after generation.</div>;
  }

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <div className="border-b border-slate-200 bg-slate-50/70 px-5 py-4">
        <p className="text-xs font-bold uppercase tracking-wide text-teal-700">Creative Plan</p>
        <h4 className="mt-1 text-xl font-black text-slate-950">{creativePlan.main_message}</h4>
      </div>

      <div className="space-y-6 px-5 py-5">
        <section className="grid gap-4 lg:grid-cols-3">
          <InfoBlock label="Product truth" value={creativePlan.product_truth} />
          <InfoBlock label="Audience pain" value={creativePlan.audience_pain} />
          <InfoBlock label="CTA" value={creativePlan.cta} />
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="field-label">Visual style</p>
          <p className="mt-2 text-sm leading-7 text-slate-800">{creativePlan.visual_style}</p>
        </section>

        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
            <p className="field-label">Safe claims</p>
            <p className="mt-2 text-sm leading-7 text-emerald-950">{formatList(creativePlan.safe_claims)}</p>
          </div>
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-4">
            <p className="field-label">Forbidden claims</p>
            <p className="mt-2 text-sm leading-7 text-rose-950">{formatList(creativePlan.forbidden_claims)}</p>
          </div>
        </section>

        <section className="border-t border-slate-200 pt-5">
          <div className="mb-3">
            <p className="text-sm font-black text-slate-950">Variant directions</p>
            <p className="mt-1 text-sm text-slate-500">These two directions feed Variant A and Variant B directly.</p>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            {creativePlan.variant_directions.map((direction, index) => (
              <article key={direction.id} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h5 className="text-sm font-black text-slate-950">Variant {index === 0 ? "A" : "B"}: {direction.name}</h5>
                  <span className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-bold text-slate-600">
                    {direction.best_for_metric}
                  </span>
                </div>
                <p className="mt-3 rounded-md bg-slate-950 px-3 py-3 text-sm font-bold leading-6 text-white">{direction.creative_angle}</p>
                <p className="mt-3 text-sm leading-6 text-slate-700">{direction.hypothesis}</p>
              </article>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
