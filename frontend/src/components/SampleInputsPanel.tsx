import type { CreateProjectValues } from "../types";

interface SampleInputsPanelProps {
  onSelect: (values: CreateProjectValues) => void;
}

const baseSample = {
  platform: "tiktok",
  duration: "20s",
  tone: "UGC, natural, realistic",
  brandColors: "",
  files: [],
};

const samples: Array<{ label: string; description: string; values: CreateProjectValues }> = [
  {
    label: "Coin Scanner App",
    description: "Mobile utility app with scan demo and estimated reference value.",
    values: {
      ...baseSample,
      productName: "Coin Scanner App",
      productCategory: "Mobile app",
      productDescription: "An app that helps users scan old coins, identify coin details, and view estimated reference value.",
      audience: "People who find old coins at home, casual collectors.",
      goal: "app_install",
      cta: "Download now and scan your old coins.",
      claimsToAvoid: "Guaranteed value, 100% accurate appraisal, you will make money.",
    },
  },
  {
    label: "Acne Serum",
    description: "Skincare routine, texture, and realistic skin concern demo.",
    values: {
      ...baseSample,
      productName: "ClearGlow Acne Serum",
      productCategory: "Skincare",
      productDescription: "A lightweight serum for people with oily and acne-prone skin. Helps improve the look of rough, bumpy skin.",
      audience: "Young adults with acne-prone skin.",
      goal: "purchase",
      cta: "Shop now.",
      claimsToAvoid: "Cures acne, guaranteed clear skin overnight.",
    },
  },
  {
    label: "Coffee Shop",
    description: "Craving, close-up drink, taste reaction, and order CTA.",
    values: {
      ...baseSample,
      productName: "Sunny Brew Iced Latte",
      productCategory: "F&B",
      productDescription: "A creamy iced latte for hot afternoons, available for delivery.",
      audience: "Office workers and students.",
      goal: "purchase",
      cta: "Order now.",
      claimsToAvoid: "Health claims.",
    },
  },
  {
    label: "Language Learning App",
    description: "Learning pain, practice method, small win, and install CTA.",
    values: {
      ...baseSample,
      productName: "SpeakEasy German",
      productCategory: "Education app",
      productDescription: "An app that helps beginners practice German speaking for daily situations.",
      audience: "Beginner German learners.",
      goal: "app_install",
      cta: "Start practicing today.",
      claimsToAvoid: "Become fluent instantly.",
    },
  },
];

export default function SampleInputsPanel({ onSelect }: SampleInputsPanelProps) {
  return (
    <section className="card p-5">
      <div className="mb-4">
        <h2 className="text-base font-bold text-slate-950">Try Sample Inputs</h2>
        <p className="text-sm text-slate-500">Fill the project form with a demo scenario.</p>
      </div>
      <div className="space-y-3">
        {samples.map((sample) => (
          <button
            key={sample.label}
            className="block w-full rounded-lg border border-slate-200 bg-white p-3 text-left transition hover:border-slate-400 hover:bg-slate-50"
            type="button"
            onClick={() => onSelect(sample.values)}
          >
            <span className="block text-sm font-bold text-slate-950">{sample.label}</span>
            <span className="mt-1 block text-xs leading-5 text-slate-500">{sample.description}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
