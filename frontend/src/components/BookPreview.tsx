/** 책 펼침면 미리보기: 순간마다 왼쪽 사진 / 오른쪽 명조 캡션 + 필름 스탬프. "이대로 인쇄된다".
 *  누가 호출: screens/Album(book 뷰).
 *  무엇을 호출: api(photoImageUrl). */
import { photoImageUrl, type Project } from "../api";

export default function BookPreview({ project, onOrder }: { project: Project; onOrder: () => void }) {
  return (
    <div className="bookview">
      {project.photos.map((m, i) => (
        <div key={m.id} className="spread">
          <div className="pg photo" style={{ backgroundImage: `url(${photoImageUrl(m.id)})` }} />
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
