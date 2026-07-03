export type VideoStatus = "draft" | "rendering" | "ready" | "failed";

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

export interface Variant {
  id: string;
  angle_id: string;
  name: string;
  duration: string;
  format: string;
  hook: string;
  script: string;
  storyboard: StoryboardScene[];
  scene_prompts: string[];
  voiceover: string;
  subtitles: string[];
  title: string;
  caption: string;
  cover_prompt: string;
  selected_playbook?: string | null;
  angle_type?: string | null;
  video_status: VideoStatus;
  video_url?: string | null;
  export_9x16_url?: string | null;
  export_1x1_url?: string | null;
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
  brandColors: string;
  files: File[];
}

export interface AnalyzeProjectResponse {
  product_intelligence: ProductIntelligenceBrief;
  product_brief: ProductBrief;
  vision_analysis: VisionAnalysis;
}
