import type { ProductBrief } from "../types";
import { formatList } from "../utils/format";

interface ProductBriefCardProps {
  brief?: ProductBrief | null;
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="field-label">{label}</dt>
      <dd className="mt-1 text-sm text-slate-800">{value}</dd>
    </div>
  );
}

export default function ProductBriefCard({ brief }: ProductBriefCardProps) {
  if (!brief) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-500">
        Product Intelligence Brief will appear here after analysis.
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Row label="Category" value={brief.category} />
      <Row label="Target audience" value={brief.target_audience} />
      <Row label="Main problem" value={brief.main_problem} />
      <Row label="Main benefit" value={brief.main_benefit} />
      <Row label="Emotional triggers" value={formatList(brief.emotional_triggers)} />
      <Row label="Functional benefits" value={formatList(brief.functional_benefits)} />
      <Row label="Proof elements" value={formatList(brief.proof_elements)} />
      <Row label="Safe claims" value={formatList(brief.safe_claims)} />
      <Row label="Claims to avoid" value={formatList(brief.claims_to_avoid)} />
      <div className="md:col-span-2">
        <Row label="Recommended visual style" value={brief.recommended_visual_style} />
      </div>
    </div>
  );
}
