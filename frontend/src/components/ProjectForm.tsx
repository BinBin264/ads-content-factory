import { useState, type FormEvent } from "react";
import FieldLabel from "./FieldLabel";
import UploadBox from "./UploadBox";
import type { CreateProjectValues } from "../types";

const initialValues: CreateProjectValues = {
  productName: "",
  productCategory: "",
  productDescription: "",
  audience: "",
  goal: "app_install",
  platform: "tiktok",
  duration: "20s",
  tone: "UGC, natural, realistic",
  cta: "",
  claimsToAvoid: "",
  files: [],
};

interface ProjectFormProps {
  loading: boolean;
  onSubmit: (values: CreateProjectValues) => Promise<void>;
}

const categoryOptions = [
  { value: "", label: "Select category" },
  { value: "Mobile app", label: "Mobile app" },
  { value: "E-commerce product", label: "E-commerce product" },
  { value: "Skincare / beauty", label: "Skincare / beauty" },
  { value: "Food & beverage", label: "Food & beverage" },
  { value: "Education / course", label: "Education / course" },
  { value: "SaaS / software", label: "SaaS / software" },
  { value: "Local service", label: "Local service" },
  { value: "Other", label: "Other" },
];

const goalOptions = [
  { value: "app_install", label: "Get app installs" },
  { value: "purchase", label: "Drive purchases" },
  { value: "lead", label: "Collect leads" },
  { value: "awareness", label: "Build awareness" },
];

const sampleInputs: Array<{ label: string; description: string; values: Omit<CreateProjectValues, "files"> }> = [
  {
    label: "Coin Scanner App",
    description: "Old coin discovery, estimated reference value, app install.",
    values: {
      productName: "Coin Scanner App",
      productCategory: "Mobile app",
      productDescription: "An app that helps users scan old coins, identify coin details, and view estimated reference value.",
      audience: "People who find old coins at home, casual coin collectors, adults with coin jars.",
      goal: "app_install",
      platform: "tiktok",
      duration: "20s",
      tone: "Natural UGC, relatable, curiosity-driven, realistic, not too polished.",
      cta: "Download now and scan your old coins.",
      claimsToAvoid: "Guaranteed value, 100% accurate appraisal, you will make money, this coin is definitely worth money.",
    },
  },
  {
    label: "ClearGlow Acne Serum",
    description: "Skincare routine, texture demo, safe beauty claims.",
    values: {
      productName: "ClearGlow Acne Serum",
      productCategory: "Skincare / beauty",
      productDescription: "A lightweight serum for people with oily and acne-prone skin. Helps improve the look of rough, bumpy skin.",
      audience: "Young adults with acne-prone skin.",
      goal: "purchase",
      platform: "tiktok",
      duration: "20s",
      tone: "Natural skincare routine, clean, realistic, soft lighting.",
      cta: "Shop now.",
      claimsToAvoid: "Cures acne, guaranteed clear skin overnight, medical treatment claims.",
    },
  },
  {
    label: "Sunny Brew Iced Latte",
    description: "F&B craving hook, close-up drink, order CTA.",
    values: {
      productName: "Sunny Brew Iced Latte",
      productCategory: "Food & beverage",
      productDescription: "A creamy iced latte for hot afternoons, available for delivery.",
      audience: "Office workers and students.",
      goal: "purchase",
      platform: "tiktok",
      duration: "20s",
      tone: "Fun, refreshing, craving-driven, energetic.",
      cta: "Order now.",
      claimsToAvoid: "Health claims.",
    },
  },
  {
    label: "SpeakEasy German",
    description: "Education app, speaking practice, beginner learning win.",
    values: {
      productName: "SpeakEasy German",
      productCategory: "Education / course",
      productDescription: "An app that helps beginners practice German speaking for daily situations.",
      audience: "Beginner German learners.",
      goal: "app_install",
      platform: "tiktok",
      duration: "20s",
      tone: "Helpful, encouraging, student-friendly, realistic.",
      cta: "Start practicing today.",
      claimsToAvoid: "Become fluent instantly, guaranteed exam pass.",
    },
  },
];

const helpText = {
  productName: "Tên sản phẩm/app/brand. Agent dùng tên này trong brief, hook, script, title và CTA.",
  productCategory: "Chọn ngành gần nhất để agent biết logic quảng cáo phù hợp. Ví dụ mobile app sẽ ưu tiên demo màn hình app, skincare sẽ tránh claim y tế.",
  productDescription: "Mô tả ngắn sản phẩm làm gì, giải quyết vấn đề gì, điểm mạnh chính. Agent dùng phần này để suy luận audience, pain point, benefit và demo moment.",
  goal: "Mục tiêu chiến dịch. Nó ảnh hưởng CTA và cách viết script: app install thì kêu gọi tải app, purchase thì đẩy mua hàng, lead thì thu thông tin.",
  platform: "Nền tảng chạy ads. Agent dùng để chọn format ngôn ngữ và nhịp video phù hợp TikTok/Reels/Shorts.",
  duration: "Độ dài video mong muốn. Agent dùng để chia thời lượng từng scene trong storyboard.",
  tone: "Phong cách giọng nói và cảm giác video. Ví dụ UGC natural realistic nghĩa là nói tự nhiên như người dùng thật, không quá quảng cáo.",
  cta: "Câu kêu gọi hành động cuối video. Ví dụ Download now, Shop now, Book a demo. Nếu để trống agent sẽ tự gợi ý.",
  claimsToAvoid: "Những câu tuyệt đối không được hứa hoặc nói quá. Agent dùng để tránh claim rủi ro trong script, hook, caption và scene prompt.",
};

export default function ProjectForm({ loading, onSubmit }: ProjectFormProps) {
  const [values, setValues] = useState<CreateProjectValues>(initialValues);

  const update = (key: keyof CreateProjectValues, value: string | File[]) => {
    setValues((current) => ({ ...current, [key]: value }));
  };

  const applySample = (sample: (typeof sampleInputs)[number]) => {
    setValues((current) => ({ ...current, ...sample.values }));
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await onSubmit(values);
  };

  return (
    <form className="card-accent p-5" onSubmit={submit}>
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-teal-700">Campaign input</p>
          <h2 className="mt-1 text-xl font-black text-slate-950">Create Project</h2>
          <p className="section-subtitle">Upload assets and define the campaign setup.</p>
        </div>
        <span className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-bold text-amber-800">MVP pipeline</span>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-teal-200 bg-teal-50 p-4 md:col-span-2">
          <div className="mb-3">
            <p className="text-xs font-bold uppercase tracking-wide text-teal-700">Try sample inputs</p>
            <p className="mt-1 text-sm text-slate-600">Fill the form with a demo scenario.</p>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            {sampleInputs.map((sample) => (
              <button
                key={sample.label}
                className="rounded-lg border border-slate-200 bg-white p-3 text-left transition hover:border-teal-300 hover:shadow-sm"
                type="button"
                onClick={() => applySample(sample)}
              >
                <span className="block text-sm font-black text-slate-950">{sample.label}</span>
                <span className="mt-1 block text-xs leading-5 text-slate-500">{sample.description}</span>
              </button>
            ))}
          </div>
        </div>
        <label className="space-y-1">
          <FieldLabel help={helpText.productName}>Product name</FieldLabel>
          <input className="field-input" required value={values.productName} onChange={(event) => update("productName", event.target.value)} />
        </label>
        <label className="space-y-1">
          <FieldLabel help={helpText.productCategory}>Product category</FieldLabel>
          <select className="field-input" value={values.productCategory} onChange={(event) => update("productCategory", event.target.value)}>
            {categoryOptions.map((option) => (
              <option key={option.value || "empty"} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1 md:col-span-2">
          <FieldLabel help={helpText.productDescription}>Product description</FieldLabel>
          <textarea
            className="field-input min-h-24 resize-y"
            value={values.productDescription}
            onChange={(event) => update("productDescription", event.target.value)}
          />
        </label>
        <label className="space-y-1">
          <FieldLabel help={helpText.goal}>Campaign objective</FieldLabel>
          <select className="field-input" value={values.goal} onChange={(event) => update("goal", event.target.value)}>
            {goalOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1">
          <FieldLabel help={helpText.platform}>Platform</FieldLabel>
          <select className="field-input" value={values.platform} onChange={(event) => update("platform", event.target.value)}>
            <option value="tiktok">TikTok</option>
            <option value="reels">Reels</option>
            <option value="shorts">Shorts</option>
          </select>
        </label>
        <label className="space-y-1">
          <FieldLabel help={helpText.duration}>Duration</FieldLabel>
          <select className="field-input" value={values.duration} onChange={(event) => update("duration", event.target.value)}>
            <option value="15s">15s</option>
            <option value="20s">20s</option>
            <option value="30s">30s</option>
          </select>
        </label>
        <label className="space-y-1">
          <FieldLabel help={helpText.tone}>Tone</FieldLabel>
          <input className="field-input" value={values.tone} onChange={(event) => update("tone", event.target.value)} />
        </label>
        <label className="space-y-1">
          <FieldLabel help={helpText.cta}>CTA</FieldLabel>
          <input className="field-input" value={values.cta} onChange={(event) => update("cta", event.target.value)} />
        </label>
        <label className="space-y-1 md:col-span-2">
          <FieldLabel help={helpText.claimsToAvoid}>Claims to avoid</FieldLabel>
          <textarea
            className="field-input min-h-20 resize-y"
            value={values.claimsToAvoid}
            onChange={(event) => update("claimsToAvoid", event.target.value)}
          />
        </label>
        <div className="md:col-span-2">
          <UploadBox files={values.files} onChange={(files) => update("files", files)} />
        </div>
      </div>

      <button className="btn-primary mt-5 w-full" disabled={loading || !values.productName.trim()}>
        {loading ? "Creating..." : "Create Project"}
      </button>
    </form>
  );
}
