import type { StoryboardScene, Variant } from "../types";

const characterConsistencyPrompt =
  "Use the uploaded character reference image as the same main creator in every scene. Keep the same face, age, hairstyle, outfit, body type, skin tone, and overall identity. Do not change the person between scenes.";

const appReferencePrompt =
  "Use the uploaded app screenshot/product image as the visual reference for the app and product. Keep the phone/app UI clean and simple; avoid generating unreadable tiny text. Leave room for text overlays to be added later.";

const productionStylePrompt =
  "Vertical 9:16 UGC ad, realistic phone-shot video, natural indoor daylight, handheld camera feel, authentic creator performance, not cinematic, not polished commercial.";

const consistencyNegativePrompt =
  "different person, changed face, changed hairstyle, different outfit, different room, inconsistent character, identity drift, face morphing, warped phone screen, unreadable app text";

export function buildKlingScenePrompt(variant: Variant, scene: StoryboardScene): string {
  return [
    characterConsistencyPrompt,
    appReferencePrompt,
    productionStylePrompt,
    "",
    `Variant: ${variant.name}`,
    `Scene ${scene.scene_number} (${scene.duration_seconds}s)`,
    `Scene objective: ${scene.objective}`,
    `Required visual: ${scene.visual_description}`,
    `Camera direction: ${scene.camera_angle}`,
    `Creator action and video prompt: ${scene.generation_prompt}`,
    `On-screen text to add later: ${scene.on_screen_text}`,
    `Voiceover line: ${scene.voiceover_line}`,
    `Transition target: ${scene.transition}`,
    "",
    `Negative prompt: ${scene.negative_prompt}, ${consistencyNegativePrompt}`,
  ].join("\n");
}

export function buildKlingPack(variant: Variant): string {
  const lines = [
    `Variant: ${variant.name}`,
    `Format: ${variant.format}`,
    `Duration: ${variant.duration}`,
    `Hook: ${variant.hook}`,
    "",
    "Reference setup:",
    "- Upload the same character reference image for every scene.",
    "- Upload the same app screenshot/product reference for every scene.",
    "- Render one scene at a time in Kling.",
    "",
    "Voiceover:",
    variant.voiceover,
    "",
    "Kling-ready scene prompts:",
  ];

  variant.storyboard.forEach((scene) => {
    lines.push("", buildKlingScenePrompt(variant, scene));
  });

  return lines.join("\n");
}
