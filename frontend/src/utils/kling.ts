import type { ProductionScene, StoryboardScene, Variant } from "../types";

function legacyScenePrompt(scene: StoryboardScene): string {
  return [
    `Scene ${scene.scene_number} (${scene.duration_seconds}s)`,
    `Objective: ${scene.objective}`,
    `Visual: ${scene.visual_description}`,
    `Camera: ${scene.camera_angle}`,
    `Prompt: ${scene.generation_prompt}`,
    `Negative: ${scene.negative_prompt}`,
  ].join("\n");
}

function productionScenePrompt(scene: ProductionScene): string {
  return [
    `Scene ${scene.scene_number} (${scene.duration_seconds}s)`,
    `Objective: ${scene.creative_objective}`,
    `Mode: ${scene.generation_mode}`,
    `References: ${scene.required_reference_assets.join(", ")}`,
    "",
    "Keyframe prompt:",
    scene.keyframe_prompt,
    "",
    "Video prompt:",
    scene.video_prompt,
    "",
    "Negative prompt:",
    scene.negative_prompt,
  ].join("\n");
}

export function buildKlingScenePrompt(variant: Variant, scene: StoryboardScene): string {
  const productionScene = variant.production_package?.production_scenes.find((item) => item.scene_number === scene.scene_number);
  return productionScene ? productionScenePrompt(productionScene) : legacyScenePrompt(scene);
}

export function buildKlingPack(variant: Variant): string {
  const lines = [`Variant: ${variant.name}`, `Hook: ${variant.hook}`, "", "Script:", variant.script];
  if (variant.production_package) {
    lines.push(
      "",
      "Character bible:",
      variant.production_package.character_bible.base_prompt,
      "",
      "Identity lock:",
      variant.production_package.character_bible.identity_lock_prompt,
      "",
      "Character reference prompts:",
      ...variant.production_package.character_reference_prompts.map(
        (prompt) => `${prompt.reference_id} (${prompt.aspect_ratio})\n${prompt.prompt}\nNegative: ${prompt.negative_prompt}`,
      ),
      "",
      "Production scenes:",
      ...variant.production_package.production_scenes.map(productionScenePrompt),
    );
    return lines.join("\n\n");
  }

  lines.push("", "Legacy storyboard prompts:", ...variant.storyboard.map(legacyScenePrompt));
  return lines.join("\n\n");
}
