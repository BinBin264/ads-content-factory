import type { ProductIntelligenceBrief } from "../types";
import { formatList } from "../utils/format";

interface ProductIntelligenceCardProps {
  intelligence?: ProductIntelligenceBrief | null;
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="field-label">{label}</dt>
      <dd className="mt-1 text-sm text-slate-800">{value}</dd>
    </div>
  );
}

export default function ProductIntelligenceCard({ intelligence }: ProductIntelligenceCardProps) {
  if (!intelligence) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-500">
        Product Intelligence will appear here after analysis.
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-3">
        <Row label="Detected product" value={intelligence.detected_product} />
        <Row label="Product type" value={intelligence.product_type} />
        <Row label="Confidence score" value={`${Math.round(intelligence.confidence_score * 100)}%`} />
        <div className="md:col-span-3">
          <Row label="Core use case" value={intelligence.core_use_case} />
        </div>
        <Row label="Primary audience" value={intelligence.primary_audience} />
        <Row label="Recommended CTA" value={intelligence.recommended_cta} />
        <Row label="Brand style notes" value={intelligence.brand_style_notes} />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Row label="Pain points" value={formatList(intelligence.pain_points)} />
        <Row label="Emotional triggers" value={formatList(intelligence.emotional_triggers)} />
        <Row label="Functional benefits" value={formatList(intelligence.functional_benefits)} />
        <Row label="Proof points" value={formatList(intelligence.proof_points)} />
        <Row label="Demo moments" value={formatList(intelligence.demo_moments)} />
        <Row label="Safe claims" value={formatList(intelligence.safe_claims)} />
        <Row label="Claims to avoid" value={formatList(intelligence.claims_to_avoid)} />
        <Row label="Visual assets detected" value={formatList(intelligence.visual_assets_detected)} />
      </div>

      <div>
        <p className="field-label mb-2">Recommended ad playbooks</p>
        <div className="grid gap-3 md:grid-cols-2">
          {intelligence.recommended_ad_playbooks.map((playbook) => (
            <div key={playbook.playbook_id} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p className="text-sm font-bold text-slate-950">{playbook.name}</p>
              <p className="mt-1 text-xs text-slate-500">{formatList(playbook.structure)}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
