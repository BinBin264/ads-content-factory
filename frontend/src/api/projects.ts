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

export async function deleteProject(id: string): Promise<void> {
  await apiClient.delete(`/api/projects/${id}`);
}
