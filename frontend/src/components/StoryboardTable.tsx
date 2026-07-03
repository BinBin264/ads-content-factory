import type { StoryboardScene } from "../types";

interface StoryboardTableProps {
  scenes: StoryboardScene[];
}

export default function StoryboardTable({ scenes }: StoryboardTableProps) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="min-w-[980px] divide-y divide-slate-200 text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-3 py-3">Scene</th>
            <th className="px-3 py-3">Duration</th>
            <th className="px-3 py-3">Objective</th>
            <th className="px-3 py-3">Visual</th>
            <th className="px-3 py-3">Camera angle</th>
            <th className="px-3 py-3">On-screen text</th>
            <th className="px-3 py-3">Voiceover</th>
            <th className="px-3 py-3">Transition</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 bg-white">
          {scenes.map((scene) => (
            <tr key={scene.scene_number} className="align-top">
              <td className="px-3 py-3 font-semibold text-slate-900">{scene.scene_number}</td>
              <td className="px-3 py-3 text-slate-700">{scene.duration_seconds}s</td>
              <td className="px-3 py-3 text-slate-700">{scene.objective}</td>
              <td className="px-3 py-3 text-slate-700">{scene.visual_description}</td>
              <td className="px-3 py-3 text-slate-700">{scene.camera_angle}</td>
              <td className="px-3 py-3 text-slate-700">{scene.on_screen_text}</td>
              <td className="px-3 py-3 text-slate-700">{scene.voiceover_line}</td>
              <td className="px-3 py-3 text-slate-700">{scene.transition}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
