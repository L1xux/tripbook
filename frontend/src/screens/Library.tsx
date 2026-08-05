/** 홈 서재. 이 기기에서 만든 여행을 책장에 진열하고, 탭하면 그 여행이 열린다.
 *  App 라우터의 루트 경로에서 열린다.
 *  lib/library의 목록과 api의 getProject를 쓴다. */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listTrips, removeTrip } from "../lib/library";
import { getProject, deleteProject, photoImageUrl, type Project } from "../api";

export default function Library() {
  const nav = useNavigate();
  const [trips, setTrips] = useState<Project[]>([]);
  const [loaded, setLoaded] = useState(false);  // 불러오는 동안 빈 서재 문구가 깜빡이지 않게 한다

  useEffect(() => {
    Promise.all(listTrips().map((id) => getProject(id).catch(() => null)))
      .then((ps) => {
        const ok = ps.filter((p): p is Project => !!p);
        // 지워졌거나 찾을 수 없는 여행은 서재 목록에서 뺀다
        listTrips().filter((id) => !ok.some((p) => p.id === id)).forEach(removeTrip);
        setTrips(ok);
      })
      .finally(() => setLoaded(true));
  }, []);

  const empty = loaded && trips.length === 0;

  const moments = trips.reduce((n, p) => n + p.photos.length, 0);
  const cover = (p: Project) => p.photos[0] ? photoImageUrl(p.photos[0].id) : undefined;
  // 순간이 많을수록 책등이 조금 더 높아진다
  const height = (p: Project) => 120 + Math.min(20, p.photos.length);

  return (
    <div style={{ padding: "70px var(--gut) 24px" }}>
      <h1 style={{ font: "800 27px/1.12 var(--sans)", letterSpacing: "-.03em" }}>여행 서재</h1>
      {empty ? (
        <p className="lib-intro">사진과 그때의 목소리를<br />한 권의 책으로 담아요.</p>
      ) : (
        <p className="lib-count">여행 {trips.length}권 · 순간 {moments}개</p>
      )}
      <div className="shelf">
        {trips.map((p) => (
          <div key={p.id} className="book-wrap" style={{ "--bh": `${height(p)}px` } as React.CSSProperties}>
            <button className="book" onClick={() => nav(`/p/${p.id}`)}
              style={cover(p) ? { backgroundImage: `url(${cover(p)})` } : { background: "#d9d2c5" }}>
              <span className="book-cap"><b>{p.title}</b><span>{p.photos.length} 순간</span></span>
            </button>
            <button className="book-del" aria-label="여행 삭제"
              onClick={(e) => {
                e.stopPropagation();
                if (!confirm("이 여행을 삭제할까요? 되돌릴 수 없어요.")) return;
                deleteProject(p.id).catch(() => {}).finally(() => {
                  removeTrip(p.id); setTrips((t) => t.filter((x) => x.id !== p.id));
                });
              }}>×</button>
          </div>
        ))}
        <button className="newbook" onClick={() => nav("/new")}><span>＋</span>새 여행</button>
      </div>
    </div>
  );
}
