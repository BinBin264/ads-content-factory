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
  generationModel?: ImageModelId | string;
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
  generationMode?: "native" | "post_voiceover" | string;
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
  referenceBindings?: ReferenceBinding[];
  qualityGate?: QualityGate;
  generationModel?: ImageModelId | string;
}

export interface KeyframeCandidate {
  id: string;
  imageUrl: string;
  mimeType?: string | null;
  warning?: string | null;
}

export type ImageGenerationJobStatus = "queued" | "running" | "retrying" | "succeeded" | "failed";

export interface ImageGenerationJob {
  id: string;
  project_id: string;
  job_type: "reference_asset" | "keyframe" | string;
  target_key: string;
  scene_index?: number | null;
  slot_id?: string | null;
  asset_type?: "character" | "location" | null;
  model_id?: ImageModelId | null;
  status: ImageGenerationJobStatus;
  progress: number;
  phase: string;
  attempt: number;
  max_attempts: number;
  error?: string | null;
  created_at: string;
  updated_at: string;
}

export type ImageModelId =
  | "nano-banana"
  | "nano-banana-2"
  | "nano-banana-pro"
  | "gpt-image-1"
  | "gpt-image-1.5"
  | "gpt-image-2"
  | "gpt-image-2-all";

export interface StorytellingScene {
  sceneIndex: number;
  narrativePurpose: string;
  title: string;
  durationSec: number;
  sceneGoal: string;
  openingState?: string;
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
  videoProgress?: number | null;
  videoStatusPayload?: Record<string, unknown> | null;
  videoReferenceUploads?: Array<{
    label?: string;
    role?: string;
    url?: string;
    source?: string | null;
  }>;
  sceneId?: string;
  clipId?: string;
  arcPosition?: string;
  dramaticFunction?: string;
  direction?: SceneDirection;
  shotContract?: ShotContract;
  promptQuality?: PromptQuality;
  takeReview?: TakeReview | null;
}

export type VideoModelId =
  | "veo3.1-pro"
  | "veo3.1-fast"
  | "grok-video-3"
  | "grok-video-3-10s";

export interface ReferenceBinding {
  stage: "keyframe" | "video" | string;
  tag: string;
  role: string;
  transfer: string;
  ignore: string;
}

export interface QualityGate {
  status: string;
  checks: string[];
  repairRule: string;
  acceptedCandidateId?: string | null;
  defects?: string[];
  notes?: string | null;
}

export interface ReviewKeyframePayload {
  verdict: "accept" | "reject";
  defects?: string[];
  notes?: string;
}

export interface SceneDirection {
  valueShift: string;
  feltIntent: string;
  lighting: string;
  atmosphere: string;
  performanceSubtext: string;
}

export interface ShotContract {
  generationMode: string;
  shotStructure: string;
  keyframeRole?: string;
  sourceCarriesState?: boolean;
  primarySpend: string;
  secondarySpend: string;
  economize: string[];
  alreadyHappened: string[];
  thisClipOnly: string[];
  reservedForLater: string[];
  plannedStartState: Record<string, unknown>;
  plannedEndState: Record<string, unknown>;
  subjectContract?: Record<string, unknown>;
  handContract?: string;
  completedDialogue?: string[];
  activeDialogue?: string[];
  postVoiceover?: string[];
  audioPhase?: string;
  nativeDialogueWordCount?: number;
  nativeDialogueWordBudget?: number;
  continuityLocks: string[];
  allowedChanges: string[];
  referenceBindings: ReferenceBinding[];
  transitionIn: string;
  transitionOut: string;
  extensionDepth: number;
}

export interface PromptQuality {
  status: "ready" | "warning" | "blocked" | string;
  score: number;
  hardFailures: string[];
  warnings: string[];
  promptLength: number;
  promptBudget: number;
}

export interface TakeReview {
  takeId: string;
  verdict: "keep";
  accepted?: boolean;
  canonAccepted?: boolean;
  reviewedAt: string;
  nextAction: string;
}

export interface StorySpine {
  logline: string;
  storyPromise: string;
  objective: string;
  initialCondition: string;
  finalOutcome: string;
  tone: string;
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
  storySpine?: StorySpine;
  worldBible?: Record<string, unknown>;
  surfaceProfile?: Record<string, unknown>;
  safetyPlan?: Record<string, unknown>;
  qualityStrategy?: Record<string, unknown>;
  sequenceState?: Record<string, unknown>;
}

export interface ReviewSceneTakePayload {
  verdict: "keep";
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
  workflow_type?: "video_ads" | "content_creation";
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
  workflowType: "video_ads" | "content_creation";
  productName: string;
  productCategory: string;
  productDescription: string;
  brief: string;
}
