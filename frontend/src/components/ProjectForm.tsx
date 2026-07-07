import { useState, type FormEvent } from "react";
import FieldLabel from "./FieldLabel";
import type { CreateProjectValues } from "../types";

const initialValues: CreateProjectValues = {
  productName: "",
  productCategory: "",
  productDescription: "",
  brief: "",
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

const helpText = {
  productName: "Product, app, or brand name. The next workflow uses this as the stable project anchor.",
  productCategory: "Choose the closest category so the planner understands product context.",
  productDescription: "Short description of what the product does, who it helps, and its main benefit.",
  brief: "Ad brief: insight, tone, CTA, must-show details, claims to avoid, references, and any special direction. Upload assets in the next project step.",
};

export default function ProjectForm({ loading, onSubmit }: ProjectFormProps) {
  const [values, setValues] = useState<CreateProjectValues>(initialValues);

  const update = (key: keyof CreateProjectValues, value: string) => {
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
          <p className="text-xs font-bold uppercase tracking-wide text-teal-700">Project setup</p>
          <h2 className="mt-1 text-xl font-black text-slate-950">Create Project</h2>
          <p className="section-subtitle">Create the project shell first. Asset upload happens inside the project workflow.</p>
        </div>
        <span className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-bold text-amber-800">Step 0</span>
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
        <label className="space-y-1 md:col-span-2">
          <FieldLabel help={helpText.brief}>Brief</FieldLabel>
          <textarea className="field-input min-h-40 resize-y" value={values.brief} onChange={(event) => update("brief", event.target.value)} />
        </label>
      </div>

      <button className="btn-primary mt-5 w-full" disabled={loading || !values.productName.trim()}>
        {loading ? "Creating..." : "Create Project"}
      </button>
    </form>
  );
}
