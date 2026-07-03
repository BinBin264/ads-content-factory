interface UploadBoxProps {
  files: File[];
  onChange: (files: File[]) => void;
}

export default function UploadBox({ files, onChange }: UploadBoxProps) {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4">
      <label className="block cursor-pointer">
        <span className="field-label">Upload files</span>
        <span className="mt-2 flex min-h-28 items-center justify-center rounded-md bg-white px-4 text-center text-sm text-slate-500">
          Product image, app screenshot, logo, brand kit, or moodboard
        </span>
        <input
          className="sr-only"
          type="file"
          multiple
          accept="image/*,.pdf,.txt,.json"
          onChange={(event) => onChange(Array.from(event.target.files ?? []))}
        />
      </label>
      {files.length > 0 ? (
        <div className="mt-3 space-y-2">
          {files.map((file) => (
            <div key={`${file.name}-${file.size}`} className="flex items-center justify-between rounded-md bg-white px-3 py-2 text-xs">
              <span className="truncate font-medium text-slate-700">{file.name}</span>
              <span className="ml-3 text-slate-400">{Math.max(1, Math.round(file.size / 1024))} KB</span>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
