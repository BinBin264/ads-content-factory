export type VideoStatus = "draft" | "package_exported" | "rendering" | "ready" | "failed";

export interface UploadedFileInfo {
  id: string;
  file_name: string;
  content_type?: string | null;
  size_bytes: number;
  path: string;
  url: string;
}

export interface ProductBrief {
  product_name: string;
  category: string;
  product_type: string;
  short_description: string;
  target_audience: string[];
  main_problem: string;
  main_benefit: string;
  emotional_triggers: string[];
  functional_benefits: string[];
  proof_elements: string[];
  safe_claims: string[];
  claims_to_avoid: string[];
  recommended_visual_style: string;
  recommended_ad_formats: string[];
}

export interface VariantDirection {
  id: string;
  name: string;
  hypothesis: string;
  creative_angle: string;
  best_for_metric: string;
}

export interface CreativePlan {
  product_truth: string;
  audience_pain: string;
  main_message: string;
  safe_claims: string[];
  forbidden_claims: string[];
  cta: string;
  visual_style: string;
  variant_directions: VariantDirection[];
}

export interface VisionAnalysis {
  detected_objects: string[];
  detected_product_type: string;
  detected_visual_style: string;
  detected_brand_colors: string[];
  detected_ui_elements: string[];
  detected_text: string[];
  confidence: number;
  notes: string[];
}

export interface Playbook {
  playbook_id: string;
  name: string;
  best_for: string[];
  structure: string[];
  recommended_angles: string[];
  scene_formula: string[];
}

export interface ProductIntelligenceBrief {
  detected_product: string;
  product_category: string;
  product_type: string;
  core_use_case: string;
  target_audience_segments: string[];
  primary_audience: string;
  pain_points: string[];
  emotional_triggers: string[];
  functional_benefits: string[];
  proof_points: string[];
  demo_moments: string[];
  visual_assets_detected: string[];
  brand_style_notes: string;
  safe_claims: string[];
  claims_to_avoid: string[];
  recommended_ad_playbooks: Playbook[];
  recommended_video_formats: string[];
  recommended_hooks: string[];
  recommended_cta: string;
  confidence_score: number;
}

export interface CreativeAngle {
  id: string;
  name: string;
  angle_type: string;
  target_audience: string;
  pain_point: string;
  emotional_trigger: string;
  hook: string;
  product_role: string;
  proof_demo_moment: string;
  cta: string;
  reason_why_it_can_work: string;
  score: number;
  hypothesis?: string | null;
  best_for_metric?: string | null;
}

export interface StoryboardScene {
  scene_number: number;
  duration_seconds: number;
  objective: string;
  visual_description: string;
  camera_angle: string;
  on_screen_text: string;
  voiceover_line: string;
  transition: string;
  generation_prompt: string;
  negative_prompt: string;
}

export interface VariantTimelineScene {
  scene: number;
  time: string;
  objective: string;
  visual: string;
  voiceover: string;
  on_screen_text: string;
  camera: string;
  transition: string;
  video_prompt: string;
  negative_prompt: string;
}

export interface CharacterPlan {
  recommended_character_type: string;
  reason: string;
  gender: string;
  age_range: string;
  ethnicity_or_look: string;
  face_details: string;
  hair: string;
  facial_hair: string;
  body_type: string;
  outfit: string;
  setting: string;
  props: string[];
  personality: string[];
  speaking_style: string;
  visual_style: string;
  role_in_ad: string;
  consistency_locks: string[];
  negative_identity_changes: string[];
}

export interface CharacterBible {
  character_id: string;
  display_name: string;
  role: string;
  gender: string;
  age_range: string;
  ethnicity_or_look: string;
  face_details: string;
  hair: string;
  facial_hair: string;
  body_type: string;
  outfit: string;
  props: string[];
  setting: string;
  personality: string[];
  speaking_style: string;
  visual_style: string;
  consistency_locks: string[];
  negative_identity_changes: string[];
  base_prompt: string;
  identity_lock_prompt: string;
}

export interface CharacterReferencePrompt {
  reference_id: string;
  purpose: string;
  aspect_ratio: string;
  prompt: string;
  negative_prompt: string;
  notes: string;
}

export interface UIOverlayItem {
  overlay_type: "app_screen" | "app_screen_overlay" | "text_overlay" | "subtitle" | "cta" | "disclaimer" | "logo" | "price_label" | "button" | "highlight";
  text: string;
  start_time: string;
  end_time: string;
  position: string;
  style_notes: string;
  safety_notes: string;
}

export interface ProductionScene {
  scene_number: number;
  duration_seconds: number;
  creative_objective: string;
  shot_type: string;
  camera_angle: string;
  generation_mode: "text_to_image" | "image_to_video" | "reference_to_video" | "overlay_only";
  required_reference_assets: string[];
  visual_description: string;
  action_description: string;
  keyframe_prompt: string;
  video_prompt: string;
  motion_instruction: string;
  consistency_instruction: string;
  negative_prompt: string;
  ui_overlay_plan: UIOverlayItem[];
  voiceover_line: string;
  on_screen_text: string;
  transition: string;
  safety_notes: string;
}

export interface EditPlan {
  total_duration: string;
  pacing_notes: string;
  music_direction: string;
  subtitle_style: string;
  cut_sequence: string[];
  export_ratios: string[];
  required_post_production_steps: string[];
  platform_notes: string;
}

export interface VideoProductionPackage {
  variant_id: string;
  creative_angle_id: string;
  character_plan: CharacterPlan;
  character_bible: CharacterBible;
  character_reference_prompts: CharacterReferencePrompt[];
  production_scenes: ProductionScene[];
  edit_plan: EditPlan;
  app_ui_overlay_notes: string;
  asset_checklist: string[];
  compliance_notes: string[];
  render_sequence: string[];
}

export type PipelineAssetType = "image" | "video" | "audio" | "app_screenshot" | "subtitle" | "json" | "zip";
export type PipelineAssetSource = "uploaded_by_user" | "generated_by_provider" | "project_upload" | "exported";
export type PipelineStage =
  | "character_reference"
  | "scene_keyframe"
  | "video_clip"
  | "app_ui_overlay"
  | "voiceover"
  | "subtitles"
  | "assembly"
  | "export";
export type PipelineToolType =
  | "image_generation"
  | "video_generation"
  | "image_editing"
  | "video_editing"
  | "tts"
  | "subtitle_generation"
  | "final_assembly"
  | "export";
export type PipelineExecutionMode = "manual_or_provider" | "provider_only" | "manual_only";
export type PipelineStepStatus = "pending" | "ready" | "running" | "completed" | "failed" | "skipped";
export type PipelineStatus = "draft" | "in_progress" | "completed" | "failed";

export interface PipelineAsset {
  asset_id: string;
  asset_key: string;
  asset_type: PipelineAssetType;
  label: string;
  url?: string | null;
  path?: string | null;
  source: PipelineAssetSource;
  source_step_id?: string | null;
  metadata: Record<string, unknown>;
}

export interface PipelineRequiredInput {
  asset_key: string;
  asset_type: string;
  label: string;
  required: boolean;
  accepted_sources: string[];
  instructions: string;
}

export interface PipelineExpectedOutput {
  asset_key: string;
  asset_type: string;
  label: string;
  file_name_hint: string;
  required_for_next_steps: string[];
}

export interface PipelineStep {
  step_id: string;
  step_number: number;
  stage: PipelineStage;
  stage_label?: string | null;
  stage_purpose?: string | null;
  title: string;
  goal: string;
  tool_type: PipelineToolType;
  execution_mode: PipelineExecutionMode;
  provider_capability?: string | null;
  source_artifacts: string[];
  required_inputs: PipelineRequiredInput[];
  prompt_to_copy?: string | null;
  negative_prompt_to_copy?: string | null;
  motion_instruction?: string | null;
  consistency_instruction?: string | null;
  settings: Record<string, unknown>;
  expected_outputs: PipelineExpectedOutput[];
  review_focus: string[];
  success_criteria: string[];
  status: PipelineStepStatus;
  output_assets: PipelineAsset[];
  manual_instructions: string[];
  provider_options: Record<string, unknown>[];
  provider_payload: Record<string, unknown>;
  error_message?: string | null;
}

export interface VariantGenerationPipeline {
  pipeline_id: string;
  variant_id: string;
  pipeline_name: string;
  pipeline_version: string;
  objective: string;
  status: PipelineStatus;
  source_artifacts: Record<string, unknown>[];
  stage_contracts: Record<string, unknown>[];
  provider_contracts: Record<string, unknown>[];
  assets: PipelineAsset[];
  steps: PipelineStep[];
}

export interface Variant {
  id: string;
  angle_id: string;
  name: string;
  hypothesis?: string | null;
  target_metric?: string | null;
  duration: string;
  format: string;
  hook: string;
  script_summary?: string | null;
  timeline: VariantTimelineScene[];
  script: string;
  storyboard: StoryboardScene[];
  scene_prompts: string[];
  voiceover: string;
  subtitles: string[];
  title: string;
  caption: string;
  cover_prompt: string;
  character_bible?: Record<string, unknown> | null;
  visual_bible?: Record<string, unknown> | null;
  asset_reference_map?: Record<string, unknown> | null;
  production_package?: VideoProductionPackage | null;
  generation_pipeline?: VariantGenerationPipeline | null;
  selected_playbook?: string | null;
  angle_type?: string | null;
  video_status: VideoStatus;
  video_url?: string | null;
  export_9x16_url?: string | null;
  export_1x1_url?: string | null;
  export_package_url?: string | null;
}

export interface Project {
  id: string;
  product_name: string;
  product_category?: string | null;
  product_description?: string | null;
  audience?: string | null;
  goal: string;
  platform: string;
  duration: string;
  tone: string;
  cta?: string | null;
  claims_to_avoid: string[];
  brand_colors: string[];
  uploaded_files: UploadedFileInfo[];
  vision_analysis?: VisionAnalysis | null;
  product_brief?: ProductBrief | null;
  product_intelligence?: ProductIntelligenceBrief | null;
  creative_plan?: CreativePlan | null;
  creative_angles: CreativeAngle[];
  variants: Variant[];
  created_at: string;
  updated_at: string;
}

export interface CreateProjectValues {
  productName: string;
  productCategory: string;
  productDescription: string;
  audience: string;
  goal: string;
  platform: string;
  duration: string;
  tone: string;
  cta: string;
  claimsToAvoid: string;
  files: File[];
}

export interface AnalyzeProjectResponse {
  product_intelligence: ProductIntelligenceBrief;
  product_brief: ProductBrief;
  vision_analysis: VisionAnalysis;
  creative_plan?: CreativePlan | null;
}
