interface FieldLabelProps {
  children: string;
  help: string;
}

export default function FieldLabel({ children, help }: FieldLabelProps) {
  return (
    <span className="field-label inline-flex items-center gap-1.5">
      {children}
      <span className="group relative inline-flex">
        <button
          className="flex h-4 w-4 items-center justify-center rounded-full border border-slate-300 bg-white text-[10px] font-black leading-none text-slate-500 transition hover:border-teal-500 hover:text-teal-700 focus:border-teal-600 focus:outline-none"
          type="button"
          aria-label={`Help: ${children}`}
        >
          ?
        </button>
        <span className="pointer-events-none absolute left-1/2 top-6 z-20 hidden w-72 -translate-x-1/2 rounded-md border border-slate-200 bg-slate-950 p-3 text-left text-xs font-medium normal-case leading-5 tracking-normal text-white shadow-soft group-hover:block group-focus-within:block">
          {help}
        </span>
      </span>
    </span>
  );
}
