import type { ProductIntelligenceBrief } from "../types";
import FieldLabel from "./FieldLabel";
import { formatList } from "../utils/format";

interface ProductIntelligenceCardProps {
  intelligence?: ProductIntelligenceBrief | null;
}

const helpText = {
  detectedProduct: "Sản phẩm/app agent nhận diện từ input và file upload. Dùng lại trong angle, script, title và prompt.",
  productType: "Nhóm sản phẩm quyết định logic quảng cáo, playbook và cấu trúc storyboard.",
  coreUseCase: "Use case chính của sản phẩm. Đây là trục để viết hook, benefit và demo.",
  primaryAudience: "Nhóm người xem chính. Creative angles và script sẽ nói theo góc nhìn nhóm này.",
  recommendedCta: "CTA đề xuất cho scene cuối, caption và export prompt.",
  brandStyleNotes: "Visual style rút ra từ upload/mô tả. Dùng cho scene prompt, cover prompt và style video.",
  painPoints: "Vấn đề của audience. Dùng để tạo problem-solution hoặc curiosity hook.",
  emotionalTriggers: "Cảm xúc kích hoạt quảng cáo như tò mò, nostalgia, trust, urgency.",
  functionalBenefits: "Lợi ích chức năng dùng cho on-screen text, claim an toàn và result scene.",
  proofPoints: "Bằng chứng/demo giúp người xem tin sản phẩm.",
  demoMoments: "Hành động cụ thể nên xuất hiện trong video và production scene.",
  safeClaims: "Các claim tương đối an toàn để script/caption có thể dùng.",
  claimsToAvoid: "Claim không được dùng vì dễ sai hoặc rủi ro policy.",
  visualAssetsDetected: "Những thứ vision thấy trong ảnh upload: UI, logo, object, text, màu.",
  recommendedAdPlaybooks: "Cấu trúc quảng cáo dùng ở phase Angles/Variants để dựng câu chuyện.",
};

function InfoLine({ label, value, help }: { label: string; value: string; help: string }) {
  return (
    <div>
      <FieldLabel help={help}>{label}</FieldLabel>
      <p className="mt-1 text-sm leading-7 text-slate-800">{value}</p>
    </div>
  );
}

function ListBlock({ label, values, help }: { label: string; values: string[]; help: string }) {
  return (
    <div>
      <FieldLabel help={help}>{label}</FieldLabel>
      <div className="mt-2 flex flex-wrap gap-2">
        {values.length ? (
          values.map((value) => (
            <span key={value} className="rounded-md border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm text-slate-700">
              {value}
            </span>
          ))
        ) : (
          <span className="text-sm text-slate-400">Not specified</span>
        )}
      </div>
    </div>
  );
}

export default function ProductIntelligenceCard({ intelligence }: ProductIntelligenceCardProps) {
  if (!intelligence) {
    return <div className="empty-state">Product Intelligence will appear here after analysis.</div>;
  }

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <div className="border-b border-slate-200 bg-slate-50/70 px-5 py-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-teal-700">Detected product</p>
            <h4 className="mt-1 text-xl font-black text-slate-950">{intelligence.detected_product}</h4>
          </div>
          <div className="flex flex-wrap gap-2">
            <span className="rounded-md border border-teal-200 bg-teal-50 px-3 py-2 text-sm font-bold text-teal-800">
              {intelligence.product_type}
            </span>
            <span className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700">
              {intelligence.product_category}
            </span>
          </div>
        </div>
      </div>

      <div className="space-y-7 px-5 py-5">
        <section className="grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(280px,0.6fr)]">
          <div className="space-y-5">
            <InfoLine label="Core use case" value={intelligence.core_use_case} help={helpText.coreUseCase} />
            <InfoLine label="Primary audience" value={intelligence.primary_audience} help={helpText.primaryAudience} />
            <InfoLine label="Brand style notes" value={intelligence.brand_style_notes} help={helpText.brandStyleNotes} />
          </div>
          <div className="rounded-lg border border-teal-200 bg-teal-50 p-4">
            <FieldLabel help={helpText.recommendedCta}>Recommended CTA</FieldLabel>
            <p className="mt-2 text-lg font-black text-teal-950">{intelligence.recommended_cta}</p>
          </div>
        </section>

        <section className="border-t border-slate-200 pt-6">
          <div className="mb-4">
            <p className="text-sm font-black text-slate-950">Creative inputs used later</p>
            <p className="mt-1 text-sm text-slate-500">These fields feed Creative Angles, Script, Character Planner, and Production Scenes.</p>
          </div>
          <div className="grid gap-5 md:grid-cols-2">
            <ListBlock label="Pain points" values={intelligence.pain_points} help={helpText.painPoints} />
            <ListBlock label="Emotional triggers" values={intelligence.emotional_triggers} help={helpText.emotionalTriggers} />
            <ListBlock label="Functional benefits" values={intelligence.functional_benefits} help={helpText.functionalBenefits} />
            <ListBlock label="Proof points" values={intelligence.proof_points} help={helpText.proofPoints} />
            <ListBlock label="Demo moments" values={intelligence.demo_moments} help={helpText.demoMoments} />
            <ListBlock label="Visual assets detected" values={intelligence.visual_assets_detected} help={helpText.visualAssetsDetected} />
          </div>
        </section>

        <section className="border-t border-slate-200 pt-6">
          <div className="grid gap-5 md:grid-cols-2">
            <ListBlock label="Safe claims" values={intelligence.safe_claims} help={helpText.safeClaims} />
            <ListBlock label="Claims to avoid" values={intelligence.claims_to_avoid} help={helpText.claimsToAvoid} />
          </div>
        </section>

        {intelligence.recommended_ad_playbooks.length ? (
          <section className="border-t border-slate-200 pt-6">
            <div className="mb-3">
              <FieldLabel help={helpText.recommendedAdPlaybooks}>Recommended ad playbooks</FieldLabel>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {intelligence.recommended_ad_playbooks.map((playbook) => (
                <div key={playbook.playbook_id} className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                  <p className="text-sm font-bold text-slate-950">{playbook.name}</p>
                  <p className="mt-2 text-sm leading-6 text-slate-700">{formatList(playbook.structure)}</p>
                </div>
              ))}
            </div>
          </section>
        ) : null}
      </div>
    </div>
  );
}
