import type { ProductIntelligenceBrief } from "../types";
import FieldLabel from "./FieldLabel";
import { formatList } from "../utils/format";

interface ProductIntelligenceCardProps {
  intelligence?: ProductIntelligenceBrief | null;
}

const helpText = {
  detectedProduct: "Agent nhận diện đây là sản phẩm/app nào từ input và file upload. Tên này sẽ được dùng lại trong angle, script, title và prompt.",
  productType: "Nhóm sản phẩm agent phân loại được, ví dụ mobile_app, skincare, ecommerce. Field này quyết định playbook quảng cáo và cấu trúc storyboard.",
  confidenceScore: "Mức tự tin của agent khi phân tích sản phẩm từ mô tả và asset. Điểm thấp nghĩa là input hoặc ảnh chưa đủ rõ.",
  coreUseCase: "Use case chính: sản phẩm giúp user làm việc gì. Đây là trục chính để viết hook, benefit và demo.",
  primaryAudience: "Nhóm người xem chính agent suy luận ra. Creative angles và script sẽ nói theo góc nhìn của nhóm này.",
  recommendedCta: "CTA agent đề xuất dựa trên campaign objective và sản phẩm. Nó sẽ đi vào scene cuối, caption và export prompt.",
  brandStyleNotes: "Ghi chú visual style agent rút ra từ brand colors, ảnh upload và mô tả. Dùng cho scene prompt, cover prompt và style video.",
  painPoints: "Các nỗi đau/vấn đề của audience. Phase Creative Angles dùng phần này để tạo problem-solution hoặc curiosity hook.",
  emotionalTriggers: "Các cảm xúc có thể kích hoạt trong quảng cáo như tò mò, nostalgia, trust, urgency. Dùng để chọn angle và tone script.",
  functionalBenefits: "Lợi ích chức năng cụ thể sản phẩm đem lại. Dùng làm claim an toàn, on-screen text và scene result.",
  proofPoints: "Bằng chứng hoặc demo moment giúp người xem tin sản phẩm. Dùng để dựng scene product demo/proof.",
  demoMoments: "Các hành động cụ thể nên xuất hiện trong video. Ví dụ mở app, scan coin, xem kết quả, save item.",
  safeClaims: "Những câu có thể nói tương đối an toàn trong ads. Script/caption nên dùng nhóm claim này.",
  claimsToAvoid: "Những claim không được dùng vì dễ sai hoặc rủi ro policy. Agent sẽ tránh khi viết hook, script, caption.",
  visualAssetsDetected: "Những thứ vision agent thấy trong ảnh upload: UI, logo, màu, object, text. Dùng làm reference cho scene prompt.",
  recommendedAdPlaybooks: "Các cấu trúc quảng cáo agent đề xuất, ví dụ Discovery & Reveal. Phase Angles/Variants dùng playbook để dựng câu chuyện.",
};

function Row({ label, value, help }: { label: string; value: string; help: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <dt>
        <FieldLabel help={help}>{label}</FieldLabel>
      </dt>
      <dd className="mt-1 text-sm text-slate-800">{value}</dd>
    </div>
  );
}

export default function ProductIntelligenceCard({ intelligence }: ProductIntelligenceCardProps) {
  if (!intelligence) {
    return <div className="empty-state">Product Intelligence will appear here after analysis.</div>;
  }

  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-3">
        <Row label="Detected product" value={intelligence.detected_product} help={helpText.detectedProduct} />
        <Row label="Product type" value={intelligence.product_type} help={helpText.productType} />
        <div className="rounded-lg border border-teal-200 bg-teal-50 p-3">
          <dt>
            <FieldLabel help={helpText.confidenceScore}>Confidence score</FieldLabel>
          </dt>
          <dd className="mt-1 text-2xl font-black text-teal-900">{Math.round(intelligence.confidence_score * 100)}%</dd>
        </div>
        <div className="md:col-span-3">
          <Row label="Core use case" value={intelligence.core_use_case} help={helpText.coreUseCase} />
        </div>
        <Row label="Primary audience" value={intelligence.primary_audience} help={helpText.primaryAudience} />
        <Row label="Recommended CTA" value={intelligence.recommended_cta} help={helpText.recommendedCta} />
        <Row label="Brand style notes" value={intelligence.brand_style_notes} help={helpText.brandStyleNotes} />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Row label="Pain points" value={formatList(intelligence.pain_points)} help={helpText.painPoints} />
        <Row label="Emotional triggers" value={formatList(intelligence.emotional_triggers)} help={helpText.emotionalTriggers} />
        <Row label="Functional benefits" value={formatList(intelligence.functional_benefits)} help={helpText.functionalBenefits} />
        <Row label="Proof points" value={formatList(intelligence.proof_points)} help={helpText.proofPoints} />
        <Row label="Demo moments" value={formatList(intelligence.demo_moments)} help={helpText.demoMoments} />
        <Row label="Safe claims" value={formatList(intelligence.safe_claims)} help={helpText.safeClaims} />
        <Row label="Claims to avoid" value={formatList(intelligence.claims_to_avoid)} help={helpText.claimsToAvoid} />
        <Row label="Visual assets detected" value={formatList(intelligence.visual_assets_detected)} help={helpText.visualAssetsDetected} />
      </div>

      <div>
        <div className="mb-2">
          <FieldLabel help={helpText.recommendedAdPlaybooks}>Recommended ad playbooks</FieldLabel>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          {intelligence.recommended_ad_playbooks.map((playbook) => (
            <div key={playbook.playbook_id} className="rounded-lg border border-amber-200 bg-amber-50 p-3">
              <p className="text-sm font-bold text-slate-950">{playbook.name}</p>
              <p className="mt-1 text-xs leading-5 text-slate-600">{formatList(playbook.structure)}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
