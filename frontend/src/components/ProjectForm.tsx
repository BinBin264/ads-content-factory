import { useEffect, useState, type FormEvent } from "react";
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
  sampleValues?: CreateProjectValues | null;
  onSubmit: (values: CreateProjectValues) => Promise<void>;
}

export default function ProjectForm({ loading, sampleValues, onSubmit }: ProjectFormProps) {
  const [values, setValues] = useState<CreateProjectValues>(initialValues);

  useEffect(() => {
    if (sampleValues) {
      setValues(sampleValues);
    }
  }, [sampleValues]);

  const update = (key: keyof CreateProjectValues, value: string | File[]) => {
    setValues((current) => ({ ...current, [key]: value }));
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await onSubmit(values);
  };

  return (
    <form className="card p-5" onSubmit={submit}>
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-slate-950">Create Project</h2>
          <p className="text-sm text-slate-500">Upload assets and define the ad target.</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="space-y-1">
          <span className="field-label">Product name</span>
          <input className="field-input" required value={values.productName} onChange={(event) => update("productName", event.target.value)} />
        </label>
        <label className="space-y-1">
          <span className="field-label">Product category</span>
          <input className="field-input" value={values.productCategory} onChange={(event) => update("productCategory", event.target.value)} />
        </label>
        <label className="space-y-1 md:col-span-2">
          <span className="field-label">Product description</span>
          <textarea
            className="field-input min-h-24 resize-y"
            value={values.productDescription}
            onChange={(event) => update("productDescription", event.target.value)}
          />
        </label>
        <label className="space-y-1 md:col-span-2">
          <span className="field-label">Audience</span>
          <input className="field-input" value={values.audience} onChange={(event) => update("audience", event.target.value)} />
        </label>
        <label className="space-y-1">
          <span className="field-label">Goal</span>
          <select className="field-input" value={values.goal} onChange={(event) => update("goal", event.target.value)}>
            <option value="app_install">App install</option>
            <option value="purchase">Purchase</option>
            <option value="lead">Lead</option>
            <option value="awareness">Awareness</option>
          </select>
        </label>
        <label className="space-y-1">
          <span className="field-label">Platform</span>
          <select className="field-input" value={values.platform} onChange={(event) => update("platform", event.target.value)}>
            <option value="tiktok">TikTok</option>
            <option value="reels">Reels</option>
            <option value="shorts">Shorts</option>
          </select>
        </label>
        <label className="space-y-1">
          <span className="field-label">Duration</span>
          <select className="field-input" value={values.duration} onChange={(event) => update("duration", event.target.value)}>
            <option value="15s">15s</option>
            <option value="20s">20s</option>
            <option value="30s">30s</option>
          </select>
        </label>
        <label className="space-y-1">
          <span className="field-label">Tone</span>
          <input className="field-input" value={values.tone} onChange={(event) => update("tone", event.target.value)} />
        </label>
        <label className="space-y-1">
          <span className="field-label">CTA</span>
          <input className="field-input" value={values.cta} onChange={(event) => update("cta", event.target.value)} />
        </label>
        <label className="space-y-1">
          <span className="field-label">Brand colors</span>
          <input className="field-input" placeholder="#111827, #22c55e" value={values.brandColors} onChange={(event) => update("brandColors", event.target.value)} />
        </label>
        <label className="space-y-1 md:col-span-2">
          <span className="field-label">Claims to avoid</span>
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
