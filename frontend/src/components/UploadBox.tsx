import FieldLabel from "./FieldLabel";

interface UploadBoxProps {
  files: File[];
  onChange: (files: File[]) => void;
}

export default function UploadBox({ files, onChange }: UploadBoxProps) {
  return (
    <div className="rounded-lg border border-dashed border-teal-300 bg-teal-50/60 p-4">
      <label className="block cursor-pointer">
        <FieldLabel help="Upload ảnh sản phẩm, screenshot app, logo, moodboard hoặc brand kit. Vision agent dùng file này để nhận diện UI, màu sắc, style và proof moment cho video.">
          Upload files
        </FieldLabel>
        <span className="mt-2 flex min-h-28 items-center justify-center rounded-md border border-white bg-white px-4 text-center text-sm font-semibold text-slate-600 shadow-sm">
          Drop product image, app screenshot, logo, brand kit, or moodboard
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
              <span className="ml-3 rounded bg-slate-100 px-2 py-1 font-bold text-slate-500">{Math.max(1, Math.round(file.size / 1024))} KB</span>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
