import type { Project } from "../types";

interface ProgressStepsProps {
  project: Project | null;
}

const steps = [
  "Project Created",
  "Product Analyzed",
  "Angles Generated",
  "Variants Generated",
  "Mock Rendered",
] as const;

export default function ProgressSteps({ project }: ProgressStepsProps) {
  const complete = [
    Boolean(project),
    Boolean(project?.product_brief),
    Boolean(project?.creative_angles.length),
    Boolean(project?.variants.length),
    Boolean(project?.variants.some((variant) => variant.video_status === "ready")),
  ];

  return (
    <div className="card p-4">
      <div className="grid gap-3 md:grid-cols-5">
        {steps.map((step, index) => (
          <div key={step} className="flex items-center gap-3">
            <div
              className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                complete[index] ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-400"
              }`}
            >
              {index + 1}
            </div>
            <div className="min-w-0">
              <p className={`truncate text-sm font-semibold ${complete[index] ? "text-slate-900" : "text-slate-400"}`}>{step}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
