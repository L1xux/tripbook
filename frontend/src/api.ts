/** 백엔드 API 클라이언트. 모든 컴포넌트는 이 파일을 통해서만 서버와 통신한다. */
const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: init?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text?.() ?? ""}`);
  return res.json();
}

export type Mood = "family_essay" | "friendship_saga" | "fantasy_adventure" | "lyrical_essay" | "comedy";
export interface Photo { id: string; sort_order: number; emotion: string | null; note: string | null;
  ai_scene_description: string | null; analysis_status: string; user_scene_correction: string | null; }
export interface Page { id: string; page_number: number; photo_id: string | null; text: string; regen_count: number; }
export interface Project { id: string; title: string; mood: string; status: string;
  order_status: string | null; photos: Photo[]; pages: Page[]; }

export const createProject = (b: { title: string; mood: Mood; start_date?: string; end_date?: string; companions?: string }) =>
  req<{ id: string }>("/api/v1/projects", { method: "POST", body: JSON.stringify(b) });
export const getProject = (id: string) => req<Project>(`/api/v1/projects/${id}`);
export const uploadPhotos = (id: string, files: File[]) => {
  const fd = new FormData();
  files.forEach((f) => fd.append("files", f));
  return req<{ photos: Photo[] }>(`/api/v1/projects/${id}/photos`, { method: "POST", body: fd });
};
export const getAnalysis = (id: string) =>
  req<{ photos: { id: string; analysis_status: string; ai_scene_description: string | null }[] }>(
    `/api/v1/projects/${id}/photos/analysis`);
export const patchPhoto = (photoId: string, b: Partial<Pick<Photo, "note" | "emotion" | "user_scene_correction">>) =>
  req(`/api/v1/photos/${photoId}`, { method: "PATCH", body: JSON.stringify(b) });
export const reorderPhotos = (id: string, photo_ids: string[]) =>
  req(`/api/v1/projects/${id}/photos/order`, { method: "PATCH", body: JSON.stringify({ photo_ids }) });
export const startWriting = (id: string) => req(`/api/v1/projects/${id}/write`, { method: "POST" });
export const writeStreamUrl = (id: string) => `${BASE}/api/v1/projects/${id}/write/stream`;
export const patchPage = (pageId: string, text: string) =>
  req(`/api/v1/pages/${pageId}`, { method: "PATCH", body: JSON.stringify({ text }) });
export const regeneratePage = (pageId: string, feedback: string) =>
  req<{ id: string; text: string; regen_count: number }>(`/api/v1/pages/${pageId}/regenerate`,
    { method: "POST", body: JSON.stringify({ feedback }) });
export const createOrder = (id: string, spec: object, shipping: object) =>
  req<{ book_uid: string; order_uid: string }>(`/api/v1/projects/${id}/order`,
    { method: "POST", body: JSON.stringify({ spec, shipping }) });
export const getOrderStatus = (id: string) =>
  req<{ order_status: string | null }>(`/api/v1/projects/${id}/order/status`);
