import { useState, type FormEvent } from "react";
import FieldLabel from "./FieldLabel";
import type { CreateProjectValues } from "../types";

const initialValues: CreateProjectValues = {
  workflowType: "video_ads",
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

export default function ProjectForm({ loading, onSubmit }: ProjectFormProps) {
  const [values, setValues] = useState<CreateProjectValues>(initialValues);
  const isContentCreation = values.workflowType === "content_creation";

  const labels = isContentCreation
    ? {
        eyebrow: "Content workflow",
        title: "Create Content Video",
        subtitle: "Describe the story you want to make. AI will analyze the script and turn it into scenes, visual references, keyframes, and video prompts.",
        name: "Content title",
        category: "",
        description: "Describe your script",
        brief: "",
        submit: "Create Content Project",
      }
    : {
        eyebrow: "Ads workflow",
        title: "Create Video Ad",
        subtitle: "Start from a product/app brief. The workflow will create references, keyframes, and ad video prompts.",
        name: "Product name",
        category: "Product category",
        description: "Product description",
        brief: "Ad brief",
        submit: "Create Ads Project",
      };

  const helpText = isContentCreation
    ? {
        productName: "Short title for this content idea. Example: Flea market coin secret.",
        productCategory: "",
        productDescription: "Describe the full story in your own words: what happens, who appears, the setting, dialogue, and the ending. AI will structure it for production.",
        brief: "",
      }
    : {
        productName: "Product, app, or brand name. The next workflow uses this as the stable project anchor.",
        productCategory: "Choose the closest category so the planner understands product context.",
        productDescription: "Short description of what the product does, who it helps, and its main benefit.",
        brief: "Ad brief: insight, tone, CTA, must-show details, claims to avoid, references, and any special direction. Upload assets in the next project step.",
      };

  const update = (key: keyof CreateProjectValues, value: string) => {
    setValues((current) => ({ ...current, [key]: value }));
  };

  const setWorkflowType = (workflowType: CreateProjectValues["workflowType"]) => {
    setValues((current) => ({
      ...current,
      workflowType,
      productCategory: "",
      brief: workflowType === "content_creation" ? "" : current.brief,
    }));
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await onSubmit(values);
  };

  const canSubmit = Boolean(values.productName.trim() && (!isContentCreation || values.productDescription.trim()));

  return (
    <form className="home-form" onSubmit={submit}>
      <div className="home-form-header">
        <div>
          <p className="home-eyebrow">{labels.eyebrow}</p>
          <h2>{labels.title}</h2>
          <p>{labels.subtitle}</p>
        </div>
      </div>

      <div className="home-mode-grid">
        <button
          className={`home-mode-option ${
            !isContentCreation ? "is-selected is-ads" : ""
          }`}
          type="button"
          onClick={() => setWorkflowType("video_ads")}
        >
          <span className="home-mode-dot" />
          <span><strong>Video Ads</strong><small>Product-led campaign workflow</small></span>
        </button>
        <button
          className={`home-mode-option ${
            isContentCreation ? "is-selected is-content" : ""
          }`}
          type="button"
          onClick={() => setWorkflowType("content_creation")}
        >
          <span className="home-mode-dot" />
          <span><strong>Content Creation</strong><small>Idea-led storytelling workflow</small></span>
        </button>
      </div>

      {isContentCreation ? (
        <>
          <div className="home-section-heading">
            <span>01</span>
            <div><strong>Script input</strong><p>Write the story naturally. AI will analyze and structure it in the next step.</p></div>
          </div>
          <div className="home-form-fields home-content-fields">
            <label className="wide-field">
              <FieldLabel help={helpText.productName}>{labels.name}</FieldLabel>
              <input
                className="field-input"
                required
                placeholder="Example: The flea market coin secret"
                value={values.productName}
                onChange={(event) => update("productName", event.target.value)}
              />
            </label>
            <label className="wide-field">
              <FieldLabel help={helpText.productDescription}>{labels.description}</FieldLabel>
              <textarea
                className="field-input resize-y"
                required
                placeholder="Describe what happens from beginning to end, including characters, actions, setting, dialogue, mood, and any visual details you care about."
                value={values.productDescription}
                onChange={(event) => update("productDescription", event.target.value)}
              />
            </label>
          </div>
        </>
      ) : (
        <>
          <div className="home-section-heading">
            <span>01</span>
            <div><strong>Project foundation</strong><p>Name the project and choose the closest category.</p></div>
          </div>
          <div className="home-form-fields">
            <label>
              <FieldLabel help={helpText.productName}>{labels.name}</FieldLabel>
              <input className="field-input" required value={values.productName} onChange={(event) => update("productName", event.target.value)} />
            </label>
            <label>
              <FieldLabel help={helpText.productCategory}>{labels.category}</FieldLabel>
              <select className="field-input" value={values.productCategory} onChange={(event) => update("productCategory", event.target.value)}>
                {categoryOptions.map((option) => (
                  <option key={option.value || "empty"} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="home-section-heading">
            <span>02</span>
            <div><strong>Creative direction</strong><p>Describe what the video must communicate and how it should feel.</p></div>
          </div>
          <div className="home-form-fields home-brief-fields">
            <label className="wide-field">
              <FieldLabel help={helpText.productDescription}>{labels.description}</FieldLabel>
              <textarea
                className="field-input min-h-24 resize-y"
                placeholder="Example: A mobile app that scans old coins and shows coin details with estimated reference values."
                value={values.productDescription}
                onChange={(event) => update("productDescription", event.target.value)}
              />
            </label>
            <label className="wide-field">
              <FieldLabel help={helpText.brief}>{labels.brief}</FieldLabel>
              <textarea
                className="field-input min-h-40 resize-y"
                placeholder="Add story, hook, audience, CTA, must-show moments, claims to avoid, and reference notes."
                value={values.brief}
                onChange={(event) => update("brief", event.target.value)}
              />
            </label>
          </div>
        </>
      )}

      <div className="home-form-footer">
        <p>Your input becomes the source of truth for every later prompt.</p>
        <button className="btn-primary" disabled={loading || !canSubmit}>
          {loading ? "Creating..." : labels.submit}
          <span aria-hidden="true">-&gt;</span>
        </button>
      </div>
    </form>
  );
}
