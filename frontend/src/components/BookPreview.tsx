/** 책 펼침면 미리보기. 왼쪽에 사진, 오른쪽에 명조 글귀를 놓아 인쇄될 모습을 그대로 보여준다.
 *  누가 호출: screens/Album의 책 화면.
 *  무엇을 호출: api의 photoImageUrl. */
import { photoImageUrl, type Project } from "../api";

export default function BookPreview({ project, onOrder }: { project: Project; onOrder: () => void }) {
  return (
    <div className="bookview">
      {project.photos.map((m, i) => (
        <div key={m.id} className="spread">
          {/* 목소리가 담긴 순간에만 QR 밴드가 인쇄된다. 백엔드 렌더러와 조건을 같게 둔다. */}
          <div className="pg photo" style={{ backgroundImage: `url(${photoImageUrl(m.id)})` }}>
            {m.has_audio && (
              <div className="qr-band">
                <span className="qr-note">스캔하면 그때 목소리</span>
                <span className="qr-mark" aria-hidden="true" />
              </div>
            )}
          </div>
          <div className="spine" />
          <div className="pg txt"><div className="q">{m.caption ?? ""}</div><div className="st">NO.{String(i + 1).padStart(2, "0")}</div></div>
        </div>
      ))}
      <div className="bottom-bar">
        <button className="btn" style={{ width: "100%" }} onClick={onOrder}>이대로 만들기</button>
      </div>
    </div>
  );
}
