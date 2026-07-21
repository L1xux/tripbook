/** 백엔드 v2 API 클라이언트. 모든 컴포넌트는 이 파일로만 서버와 통신한다.
 *  누가 호출: screens/*, components/* (프론트 전체).
 *  무엇을 호출: FastAPI v2 (/api/v1/*) — 프로젝트/사진/음성/캡션/주문. */
const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: init?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    // 백엔드가 detail에 담아주는 한국어 메시지를 그대로 사용자에게 보여준다
    let msg = `요청 실패 (${res.status})`;
    try { const b = await res.json(); if (typeof b.detail === "string") msg = b.detail; } catch { /* keep */ }
    throw new Error(msg);
  }
  return res.json();
}

export interface Moment { id: string; sort_order: number; emotion: string | null; note: string | null;
  caption: string | null; transcript: string | null; suggested_emotion: string | null; analysis_status: string; }
export interface Recipient { id: string; name: string; phone: string | null; address: string;
  gift_message: string | null; order_status: string | null; }
export interface Project { id: string; title: string; status: string; cover_line: string | null;
  reveal_mode: string; start_date: string | null; end_date: string | null; companions: string | null;
  order_status: string | null; photos: Moment[]; recipients: Recipient[]; }

export const createProject = (b: { title: string; start_date?: string; end_date?: string; companions?: string; cover_line?: string }) =>
  req<{ id: string }>("/api/v1/projects", { method: "POST", body: JSON.stringify(b) });
export const getProject = (id: string) => req<Project>(`/api/v1/projects/${id}`);
export const uploadPhotos = (id: string, files: File[]) => {
  const fd = new FormData(); files.forEach((f) => fd.append("files", f));
  return req<{ photos: Moment[] }>(`/api/v1/projects/${id}/photos`, { method: "POST", body: fd });
};
export const photoImageUrl = (momentId: string) => `${BASE}/api/v1/photos/${momentId}/image`;
export const uploadAudio = (momentId: string, blob: Blob) => {
  const fd = new FormData(); fd.append("file", blob, "voice.m4a");
  return req<{ id: string }>(`/api/v1/moments/${momentId}/audio`, { method: "POST", body: fd });
};
export const getAnalysis = (id: string) =>
  req<{ photos: { id: string; analysis_status: string; suggested_emotion: string | null; caption: string | null; transcript: string | null }[] }>(
    `/api/v1/projects/${id}/photos/analysis`);
export const patchMoment = (momentId: string, b: Partial<Pick<Moment, "emotion" | "note" | "caption">>) =>
  req(`/api/v1/moments/${momentId}`, { method: "PATCH", body: JSON.stringify(b) });
export const reorderMoments = (id: string, photo_ids: string[]) =>
  req(`/api/v1/projects/${id}/photos/order`, { method: "PATCH", body: JSON.stringify({ photo_ids }) });
export const addRecipient = (id: string, b: { name: string; address: string; phone?: string; postal_code?: string; gift_message?: string }) =>
  req<{ id: string }>(`/api/v1/projects/${id}/recipients`, { method: "POST", body: JSON.stringify(b) });
export const removeRecipient = (rid: string) => req(`/api/v1/recipients/${rid}`, { method: "DELETE" });
export const createOrder = (id: string, spec: object, shipping: object) =>
  req<{ book_uid: string; orders: { to: string; order_uid: string }[] }>(`/api/v1/projects/${id}/order`,
    { method: "POST", body: JSON.stringify({ spec, shipping }) });
export const getOrderStatus = (id: string) =>
  req<{ order_status: string | null; recipients: { name: string; order_status: string | null }[] }>(
    `/api/v1/projects/${id}/order/status`);
