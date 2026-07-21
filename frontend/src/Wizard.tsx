/** 위자드 공용 셸: 차례(목차) 헤더 + 뒤로가기. 지나온 단계는 탭해서 돌아갈 수 있다. */
import type { ReactNode } from "react";
import { useNavigate, useParams } from "react-router-dom";

const STEPS = [
  { key: "info", label: "정보" },
  { key: "photos", label: "사진" },
  { key: "writing", label: "집필" },
  { key: "review", label: "퇴고" },
  { key: "order", label: "주문" },
] as const;

type StepKey = (typeof STEPS)[number]["key"];

export default function Wizard({ step, children }: { step: StepKey; children: ReactNode }) {
  const nav = useNavigate();
  const { id } = useParams();
  const idx = STEPS.findIndex((s) => s.key === step);

  const goTo = (key: StepKey) => {
    if (key === "info" || !id) return nav("/");
    nav(`/p/${id}/${key}`);
  };

  return (
    <div>
      <header className="toc">
        <div className="toc-top">
          {idx > 0 && (
            <button className="toc-back" aria-label="이전 단계로"
              onClick={() => goTo(STEPS[idx - 1].key)}>←</button>
          )}
          <span className="toc-title">Tripbook</span>
        </div>
        <nav className="toc-steps" aria-label="진행 단계">
          {STEPS.map((s, i) => (
            <button key={s.key} disabled={i >= idx}
              className={"toc-step" + (i === idx ? " now" : i < idx ? " done" : "")}
              onClick={() => goTo(s.key)}>
              {s.label}
            </button>
          ))}
        </nav>
      </header>
      {children}
    </div>
  );
}
