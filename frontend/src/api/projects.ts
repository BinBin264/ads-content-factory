import { apiClient } from "./client";
import type { CreateProjectValues, PlanCreation, Project } from "../types";

function appendIfPresent(formData: FormData, key: string, value: string): void {
  const trimmed = value.trim();
  if (trimmed) {
    formData.append(key, trimmed);
  }
}

export async function createProject(values: CreateProjectValues): Promise<Project> {
  const formData = new FormData();
  formData.append("product_name", values.productName.trim());
  appendIfPresent(formData, "product_category", values.productCategory);
  appendIfPresent(formData, "product_description", values.productDescription);
  appendIfPresent(formData, "brief", values.brief);

  const response = await apiClient.post<Project>("/api/projects", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function listProjects(): Promise<Project[]> {
  const response = await apiClient.get<Project[]>("/api/projects");
  return response.data;
}

export async function getProject(id: string): Promise<Project> {
  const response = await apiClient.get<Project>(`/api/projects/${id}`);
  return response.data;
}

export async function generatePlanCreation(id: string): Promise<PlanCreation> {
  const response = await apiClient.post<PlanCreation>(`/api/projects/${id}/plan-creation`);
  return response.data;
}

export async function uploadProjectFiles(id: string, files: File[]): Promise<Project> {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append("files", file);
  });
  const response = await apiClient.post<Project>(`/api/projects/${id}/uploads`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function updateProductReference(
  id: string,
  referenceId: string,
  payload: Record<string, unknown>,
): Promise<Project> {
  const response = await apiClient.patch<Project>(`/api/projects/${id}/product-references/${referenceId}`, payload);
  return response.data;
}

export async function updateScene(id: string, sceneIndex: number, payload: Record<string, unknown>): Promise<Project> {
  const response = await apiClient.patch<Project>(`/api/projects/${id}/scenes/${sceneIndex}`, payload);
  return response.data;
}

export async function rewriteScene(id: string, sceneIndex: number, instruction: string): Promise<Project> {
  const response = await apiClient.post<Project>(`/api/projects/${id}/scenes/${sceneIndex}/rewrite`, { instruction });
  return response.data;
}

export async function updateSceneVideoPrompt(id: string, sceneIndex: number, finalVideoPrompt: string): Promise<Project> {
  const response = await apiClient.patch<Project>(`/api/projects/${id}/scenes/${sceneIndex}/video-prompt`, { finalVideoPrompt });
  return response.data;
}

export async function regenerateSceneVideoPrompt(id: string, sceneIndex: number): Promise<Project> {
  const response = await apiClient.post<Project>(`/api/projects/${id}/scenes/${sceneIndex}/video-prompt/regenerate`);
  return response.data;
}

export async function updateKeyframePromptSlot(
  id: string,
  sceneIndex: number,
  slotId: string,
  payload: Record<string, unknown>,
): Promise<Project> {
  const response = await apiClient.patch<Project>(`/api/projects/${id}/scenes/${sceneIndex}/keyframe-slots/${slotId}`, payload);
  return response.data;
}

export async function selectKeyframeCandidate(
  id: string,
  sceneIndex: number,
  slotId: string,
  payload: { imageUrl?: string; fileId?: string; candidateId?: string },
): Promise<Project> {
  const response = await apiClient.post<Project>(`/api/projects/${id}/scenes/${sceneIndex}/keyframe-slots/${slotId}/select`, payload);
  return response.data;
}

export async function generateReferenceAssetImage(id: string, assetType: "character" | "location"): Promise<Project> {
  const response = await apiClient.post<Project>(`/api/projects/${id}/reference-assets/${assetType}/generate`);
  return response.data;
}

export async function updateReferenceAsset(id: string, assetType: "character" | "location", payload: Record<string, unknown>): Promise<Project> {
  const response = await apiClient.patch<Project>(`/api/projects/${id}/reference-assets/${assetType}`, payload);
  return response.data;
}

export async function uploadReferenceAssetImage(id: string, assetType: "character" | "location", file: File): Promise<Project> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await apiClient.post<Project>(`/api/projects/${id}/reference-assets/${assetType}/upload`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function generateKeyframeSlotImage(id: string, sceneIndex: number, slotId: string): Promise<Project> {
  const response = await apiClient.post<Project>(`/api/projects/${id}/scenes/${sceneIndex}/keyframe-slots/${slotId}/generate`);
  return response.data;
}

export async function uploadKeyframeSlotImage(id: string, sceneIndex: number, slotId: string, file: File): Promise<Project> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await apiClient.post<Project>(`/api/projects/${id}/scenes/${sceneIndex}/keyframe-slots/${slotId}/upload`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function generateSceneVideo(id: string, sceneIndex: number): Promise<Project> {
  const response = await apiClient.post<Project>(`/api/projects/${id}/scenes/${sceneIndex}/video`);
  return response.data;
}

export async function uploadSceneVideo(id: string, sceneIndex: number, file: File): Promise<Project> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await apiClient.post<Project>(`/api/projects/${id}/scenes/${sceneIndex}/video/upload`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function deleteProject(id: string): Promise<void> {
  await apiClient.delete(`/api/projects/${id}`);
}
