import { apiClient } from "./client";
import type { AnalyzeProjectResponse, CreateProjectValues, CreativeAngle, Project, Variant, VariantGenerationPipeline } from "../types";

function appendIfPresent(formData: FormData, key: string, value: string): void {
  const trimmed = value.trim();
  if (trimmed) {
    formData.append(key, trimmed);
  }
}

function appendListField(formData: FormData, key: string, value: string): void {
  value
    .split(/[,\n;]/)
    .map((item) => item.trim())
    .filter(Boolean)
    .forEach((item) => formData.append(key, item));
}

export async function createProject(values: CreateProjectValues): Promise<Project> {
  const formData = new FormData();
  formData.append("product_name", values.productName.trim());
  appendIfPresent(formData, "product_category", values.productCategory);
  appendIfPresent(formData, "product_description", values.productDescription);
  appendIfPresent(formData, "audience", values.audience);
  formData.append("goal", values.goal);
  formData.append("platform", values.platform);
  formData.append("duration", values.duration);
  appendIfPresent(formData, "tone", values.tone);
  appendIfPresent(formData, "cta", values.cta);
  appendListField(formData, "claims_to_avoid", values.claimsToAvoid);

  values.files.forEach((file) => {
    formData.append("files", file);
  });

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

export async function analyzeProject(id: string): Promise<AnalyzeProjectResponse> {
  const response = await apiClient.post<AnalyzeProjectResponse>(`/api/projects/${id}/analyze`);
  return response.data;
}

export async function generateAngles(id: string): Promise<CreativeAngle[]> {
  const response = await apiClient.post<CreativeAngle[]>(`/api/projects/${id}/angles`);
  return response.data;
}

export async function generateVariants(id: string, angleIds?: string[]): Promise<Variant[]> {
  const body = angleIds && angleIds.length > 0 ? { angle_ids: angleIds, variant_count: 2 } : { variant_count: 2 };
  const response = await apiClient.post<Variant[]>(`/api/projects/${id}/generate-variants`, body);
  return response.data;
}

export async function renderProject(id: string): Promise<Project> {
  const response = await apiClient.post<Project>(`/api/projects/${id}/render`);
  return response.data;
}

export async function exportProductionPackage(id: string): Promise<Project> {
  const response = await apiClient.post<Project>(`/api/projects/${id}/export-production-package`);
  return response.data;
}

export async function getVariantPipeline(projectId: string, variantId: string): Promise<VariantGenerationPipeline> {
  const response = await apiClient.get<VariantGenerationPipeline>(`/api/projects/${projectId}/variants/${variantId}/pipeline`);
  return response.data;
}

export async function uploadPipelineStepResult(
  projectId: string,
  variantId: string,
  stepId: string,
  file: File,
  assetKey?: string,
  notes?: string,
): Promise<Project> {
  const formData = new FormData();
  formData.append("file", file);
  if (assetKey?.trim()) {
    formData.append("asset_key", assetKey.trim());
  }
  if (notes?.trim()) {
    formData.append("notes", notes.trim());
  }
  const response = await apiClient.post<Project>(`/api/projects/${projectId}/variants/${variantId}/pipeline/steps/${stepId}/upload-result`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function runPipelineStep(projectId: string, variantId: string, stepId: string): Promise<Project> {
  const response = await apiClient.post<Project>(`/api/projects/${projectId}/variants/${variantId}/pipeline/steps/${stepId}/run`);
  return response.data;
}

export async function runVariantPipeline(projectId: string, variantId: string): Promise<Project> {
  const response = await apiClient.post<Project>(`/api/projects/${projectId}/variants/${variantId}/pipeline/run`);
  return response.data;
}

export async function deleteProject(id: string): Promise<void> {
  await apiClient.delete(`/api/projects/${id}`);
}
