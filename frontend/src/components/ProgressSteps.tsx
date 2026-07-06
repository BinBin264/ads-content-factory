import type { Project } from "../types";

interface ProgressStepsProps {
  project: Project | null;
}

const steps = [
  { label: "Creative Plan" },
  { label: "Variant A" },
  { label: "Variant B" },
  { label: "Package / Render" },
] as const;

export default function ProgressSteps({ project }: ProgressStepsProps) {
  const complete = [
    Boolean(project?.creative_plan),
    Boolean(project?.variants[0]),
    Boolean(project?.variants[1]),
    Boolean(project?.variants.some((variant) => variant.production_package || variant.video_status === "ready")),
  ];
  const currentIndex = complete.findIndex((isComplete) => !isComplete);

  return (
    <div className="card-accent p-4">
      <div className="grid gap-3 md:grid-cols-4">
        {steps.map((step, index) => {
          const isComplete = complete[index];
          const isCurrent = !isComplete && index === currentIndex;

          return (
          <div
            key={step.label}
            className={`rounded-lg border p-3 ${
              isComplete ? "border-emerald-200 bg-emerald-50" : isCurrent ? "border-rose-200 bg-rose-50" : "border-slate-200 bg-slate-50"
            }`}
          >
            <div
              className={`mb-3 flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-xs font-black ${
                isComplete ? "bg-emerald-600 text-white" : isCurrent ? "bg-rose-600 text-white" : "bg-slate-200 text-slate-500"
              }`}
            >
              {index + 1}
            </div>
            <div className="min-w-0">
              <p className={`truncate text-sm font-bold ${isComplete || isCurrent ? "text-slate-900" : "text-slate-400"}`}>{step.label}</p>
              <p className={`mt-1 text-xs ${isCurrent ? "font-bold text-rose-700" : "text-slate-400"}`}>
                {isComplete ? "Complete" : isCurrent ? "In progress" : "Waiting"}
              </p>
            </div>
          </div>
          );
        })}
      </div>
    </div>
  );
}
