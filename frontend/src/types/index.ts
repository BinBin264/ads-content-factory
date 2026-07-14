export interface UploadedFileInfo {
  id: string;
  file_name: string;
  content_type?: string | null;
  size_bytes: number;
  path: string;
  url: string;
}

export interface StorytellingProductAnalysis {
  productType: string;
  visibleElements: string[];
  coreBenefit: string;
  brandOrVisualCues: string[];
  doNotAssume: string[];
  productLockPrompt: string;
}

export interface ProductReference {
  id: string;
  name: string;
  sourceFileName?: string;
  referenceLabel?: string;
  kind: string;
  visualDescription: string;
  lockPrompt: string;
  useWhen: string;
  isPrimary: boolean;
}

export interface ReferenceAsset {
  name: string;
  description: string;
  imagePrompt: string;
  consistencyPrompt: string;
  status?: string;
  imageUrl?: string | null;
  candidateImages?: string[];
}

export interface StorytellingCamera {
  selected: string;
  shot: string;
  movement: string;
  composition: string;
  alternatives: string[];
}

export interface VoiceLine {
  speaker: string;
  timing: string;
  actionState: string;
  emotion: string;
  delivery: string;
  line: string;
}

export interface KeyframePrompt {
  id: string;
  label: string;
  timing: string;
  purpose: string;
  prompt: string;
  productReferenceIds: string[];
  stale?: boolean;
  candidates?: KeyframeCandidate[];
  selectedCandidateId?: string | null;
  selectedImageUrl?: string | null;
}

export interface KeyframeCandidate {
  id: string;
  imageUrl: string;
  mimeType?: string | null;
  warning?: string | null;
}

export interface StorytellingScene {
  sceneIndex: number;
  narrativePurpose: string;
  title: string;
  durationSec: number;
  sceneGoal: string;
  visualAction: string;
  productMoment: string;
  characterAction: string;
  locationUse: string;
  camera: StorytellingCamera;
  voiceLines: VoiceLine[];
  ambientAudio: string;
  onScreenText: string;
  timingBeats: string[];
  keyframePrompts: KeyframePrompt[];
  finalVideoPrompt: string;
  negativeRules: string[];
  keyframePromptStale?: boolean;
  finalVideoPromptStale?: boolean;
  status?: string;
  videoUrl?: string | null;
  videoError?: string | null;
  videoProvider?: string | null;
  videoModel?: string | null;
  videoJobId?: string | null;
  videoRatio?: string | null;
  videoDuration?: string | null;
  videoMode?: string | null;
  videoResolution?: string | null;
  videoStatusPayload?: Record<string, unknown> | null;
  videoReferenceUploads?: Array<{
    label?: string;
    role?: string;
    url?: string;
    source?: string | null;
  }>;
}

export interface PlanCreation {
  product_truth?: string;
  audience_pain?: string;
  main_message?: string;
  safe_claims?: string[];
  forbidden_claims?: string[];
  cta?: string;
  visual_style?: string;
  productAnalysis?: StorytellingProductAnalysis | null;
  productReferences?: ProductReference[];
  primaryCharacter?: ReferenceAsset | null;
  primaryLocation?: ReferenceAsset | null;
  scenes?: StorytellingScene[];
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

export interface Project {
  id: string;
  product_name: string;
  product_category?: string | null;
  product_description?: string | null;
  brief?: string | null;
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
  creative_plan?: PlanCreation | null;
  created_at: string;
  updated_at: string;
}

export interface CreateProjectValues {
  productName: string;
  productCategory: string;
  productDescription: string;
  brief: string;
}
