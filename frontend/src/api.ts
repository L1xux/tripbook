/** 백엔드 v2 API 클라이언트. 모든 컴포넌트는 이 파일로만 서버와 통신한다.
 *  누가 호출: 프론트 전체의 화면과 컴포넌트.
 *  무엇을 호출: 백엔드의 /api/v1 엔드포인트. */
// 터널이나 프록시를 거칠 때는 VITE_API_BASE를 빈 값으로 두어 같은 오리진으로 보낸다.
const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8273";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: init?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    // 백엔드가 detail에 담아준 한국어 메시지를 그대로 보여준다
    let msg = `요청 실패 (${res.status})`;
    try { const b = await res.json(); if (typeof b.detail === "string") msg = b.detail; } catch { /* keep */ }
    throw new Error(msg);
  }
  return res.json();
}

export interface Moment { id: string; sort_order: number; emotion: string | null; note: string | null;
  caption: string | null; transcript: string | null; suggested_emotion: string | null; analysis_status: string; has_audio: boolean; }
export interface Recipient { id: string; name: string; phone: string | null; address: string;
  gift_message: string | null; order_status: string | null; }
export interface Project { id: string; title: string; status: string; cover_line: string | null;
  emotion_arc: string | null; reveal_mode: string; start_date: string | null; end_date: string | null;
  companions: string | null; order_status: string | null; photos: Moment[]; recipients: Recipient[]; }

export const createProject = (b: { title: string; start_date?: string; end_date?: string; companions?: string; cover_line?: string }) =>
  req<{ id: string }>("/api/v1/projects", { method: "POST", body: JSON.stringify(b) });
export const getProject = (id: string) => req<Project>(`/api/v1/projects/${id}`);
export const generateArc = (id: string) => req<{ arc: string | null }>(`/api/v1/projects/${id}/emotion-arc`, { method: "POST" });
export const deleteProject = (id: string) => req(`/api/v1/projects/${id}`, { method: "DELETE" });
export const deleteMoment = (momentId: string) => req(`/api/v1/moments/${momentId}`, { method: "DELETE" });
export const uploadPhotos = (id: string, files: File[]) => {
  const fd = new FormData(); files.forEach((f) => fd.append("files", f));
  return req<{ photos: Moment[] }>(`/api/v1/projects/${id}/photos`, { method: "POST", body: fd });
};
export const photoImageUrl = (momentId: string) => `${BASE}/api/v1/photos/${momentId}/image`;
export const uploadAudio = (momentId: string, blob: Blob) => {
  // 서버가 이 확장자로 저장하고 Whisper가 그걸로 포맷을 판별하므로 실제 녹음 포맷을 따른다
  const t = blob.type;
  const ext = t.includes("mp4") || t.includes("m4a") ? "m4a" : t.includes("ogg") ? "ogg" : "webm";
  const fd = new FormData(); fd.append("file", blob, `voice.${ext}`);
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
export const patchRecipient = (rid: string, b: { name?: string; address?: string; phone?: string; postal_code?: string; gift_message?: string }) =>
  req(`/api/v1/recipients/${rid}`, { method: "PATCH", body: JSON.stringify(b) });
// 판형과 단가는 서버가 Sweetbook에서 받아 내려준다. 프론트는 값을 들고 있지 않는다.
export interface BookSpec { name: string; price: number; page_min: number; page_max: number | null; page_increment: number }
export const getBookSpec = (pages?: number) =>
  req<BookSpec>(`/api/v1/book-spec${pages ? `?pages=${pages}` : ""}`);
export const createOrder = (id: string, shipping: object) =>
  req<{ book_uid: string; orders: { to: string; order_uid: string }[] }>(`/api/v1/projects/${id}/order`,
    { method: "POST", body: JSON.stringify({ shipping }) });
export const getOrderStatus = (id: string) =>
  req<{ order_status: string | null; cancellable: boolean; recipients: { name: string; order_status: string | null }[] }>(
    `/api/v1/projects/${id}/order/status`);
export const cancelOrder = (id: string, reason: string) =>
  req<{ ok: boolean; cancelled: number }>(`/api/v1/projects/${id}/order/cancel`,
    { method: "POST", body: JSON.stringify({ reason }) });
export interface PublicMoment { id: string; caption: string | null; transcript: string | null;
  emotion: string | null; project_title: string; has_audio: boolean; }
export const audioUrl = (momentId: string) => `${BASE}/api/v1/moments/${momentId}/audio`;
export const getMoment = (id: string) => req<PublicMoment>(`/api/v1/moments/${id}`);
