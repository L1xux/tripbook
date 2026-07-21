/** 계정 없는 MVP의 "내 서재" — 이 기기에서 만든 여행 id 목록을 localStorage에 보관.
 *  누가 호출: screens/Library(목록), screens/NewTrip(생성 시 추가).
 *  무엇을 호출: 브라우저 localStorage. */
const KEY = "tripbook.trips";
export const listTrips = (): string[] => { try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch { return []; } };
export const addTrip = (id: string) => { const t = listTrips().filter((x) => x !== id); localStorage.setItem(KEY, JSON.stringify([id, ...t])); };
export const removeTrip = (id: string) => localStorage.setItem(KEY, JSON.stringify(listTrips().filter((x) => x !== id)));
