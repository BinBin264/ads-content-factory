import type { Project } from "../types";

interface ProgressStepsProps {
  project: Project | null;
}

const steps = [
  { label: "Project Created", color: "bg-teal-600" },
  { label: "Product Analyzed", color: "bg-amber-500" },
  { label: "Angles Generated", color: "bg-rose-500" },
  { label: "Variants Generated", color: "bg-indigo-600" },
  { label: "Video Rendered", color: "bg-emerald-600" },
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
    <div className="card-accent p-4">
      <div className="grid gap-3 md:grid-cols-5">
        {steps.map((step, index) => (
          <div key={step.label} className={`rounded-lg border p-3 ${complete[index] ? "border-slate-200 bg-white" : "border-slate-200 bg-slate-50"}`}>
            <div
              className={`mb-3 flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-xs font-black ${
                complete[index] ? `${step.color} text-white` : "bg-slate-200 text-slate-500"
              }`}
            >
              {index + 1}
            </div>
            <div className="min-w-0">
              <p className={`truncate text-sm font-bold ${complete[index] ? "text-slate-900" : "text-slate-400"}`}>{step.label}</p>
              <p className="mt-1 text-xs text-slate-400">{complete[index] ? "Complete" : "Waiting"}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
