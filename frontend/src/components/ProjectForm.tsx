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
  brandColors: "",
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

const helpText = {
  productName: "Tên sản phẩm/app/brand. Agent dùng tên này trong brief, hook, script, title và CTA.",
  productCategory: "Chọn ngành gần nhất để agent biết logic quảng cáo phù hợp. Ví dụ mobile app sẽ ưu tiên demo màn hình app, skincare sẽ tránh claim y tế.",
  productDescription: "Mô tả ngắn sản phẩm làm gì, giải quyết vấn đề gì, điểm mạnh chính. Agent dùng phần này để suy luận audience, pain point, benefit và demo moment.",
  goal: "Mục tiêu chiến dịch. Nó ảnh hưởng CTA và cách viết script: app install thì kêu gọi tải app, purchase thì đẩy mua hàng, lead thì thu thông tin.",
  platform: "Nền tảng chạy ads. Agent dùng để chọn format ngôn ngữ và nhịp video phù hợp TikTok/Reels/Shorts.",
  duration: "Độ dài video mong muốn. Agent dùng để chia thời lượng từng scene trong storyboard.",
  tone: "Phong cách giọng nói và cảm giác video. Ví dụ UGC natural realistic nghĩa là nói tự nhiên như người dùng thật, không quá quảng cáo.",
  cta: "Câu kêu gọi hành động cuối video. Ví dụ Download now, Shop now, Book a demo. Nếu để trống agent sẽ tự gợi ý.",
  brandColors: "Màu nhận diện thương hiệu, nhập mã màu hoặc tên màu. Agent dùng để gợi ý visual style, overlay, cover prompt và giữ cảm giác đúng brand.",
  claimsToAvoid: "Những câu tuyệt đối không được hứa hoặc nói quá. Agent dùng để tránh claim rủi ro trong script, hook, caption và scene prompt.",
};

export default function ProjectForm({ loading, onSubmit }: ProjectFormProps) {
  const [values, setValues] = useState<CreateProjectValues>(initialValues);

  const update = (key: keyof CreateProjectValues, value: string | File[]) => {
    setValues((current) => ({ ...current, [key]: value }));
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
        <label className="space-y-1">
          <FieldLabel help={helpText.brandColors}>Brand colors</FieldLabel>
          <input className="field-input" placeholder="#111827, #22c55e" value={values.brandColors} onChange={(event) => update("brandColors", event.target.value)} />
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
