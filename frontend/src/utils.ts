/** 컴포넌트 공용 유틸. Step2/Step4가 같은 리스트-패치 로직을 세 번 복제하지 않게 한다. */

/** id가 일치하는 항목만 patch를 병합한 새 배열을 돌려준다. */
export function patchById<T extends { id: string }>(list: T[], id: string, patch: Partial<NoInfer<T>>): T[] {
  return list.map((item) => (item.id === id ? { ...item, ...patch } : item));
}
