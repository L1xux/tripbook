/** 계정이 없으므로 이 기기에서 만든 여행 id만 localStorage에 보관한다.
 *  누가 호출: screens의 Library와 NewTrip.
 *  무엇을 호출: 브라우저 localStorage. */
const KEY = "tripbook.trips";
export const listTrips = (): string[] => { try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch { return []; } };
export const addTrip = (id: string) => { const t = listTrips().filter((x) => x !== id); localStorage.setItem(KEY, JSON.stringify([id, ...t])); };
export const removeTrip = (id: string) => localStorage.setItem(KEY, JSON.stringify(listTrips().filter((x) => x !== id)));
