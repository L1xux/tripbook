/** 홈(서재): 이 기기에서 만든 여행을 책장에 책처럼 진열. 탭하면 그 여행이 열린다.
 *  누가 호출: App 라우터(/).
 *  무엇을 호출: lib/library(목록), api(getProject/photoImageUrl). */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listTrips, removeTrip } from "../lib/library";
import { getProject, photoImageUrl, type Project } from "../api";

export default function Library() {
  const nav = useNavigate();
  const [trips, setTrips] = useState<Project[]>([]);

  useEffect(() => {
    Promise.all(listTrips().map((id) => getProject(id).catch(() => null)))
      .then((ps) => {
        const ok = ps.filter((p): p is Project => !!p);
        // 삭제됐거나 못 찾는 여행 id는 서재에서 청소
        listTrips().filter((id) => !ok.some((p) => p.id === id)).forEach(removeTrip);
        setTrips(ok);
      });
  }, []);

  const cover = (p: Project) => p.photos[0] ? photoImageUrl(p.photos[0].id) : undefined;

  return (
    <div style={{ padding: "70px 20px 24px" }}>
      <h1 style={{ font: "800 27px/1.12 var(--sans)", letterSpacing: "-.03em" }}>여행 서재</h1>
      <p style={{ font: "400 12px/1.4 var(--mono)", color: "var(--soft)", margin: "8px 2px 26px" }}>
        {trips.length} TRIPS
      </p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 13 }}>
        {trips.map((p) => (
          <button key={p.id} className="book" onClick={() => nav(`/p/${p.id}`)}
            style={cover(p) ? { backgroundImage: `url(${cover(p)})` } : { background: "#d9d2c5" }}>
            <span className="book-cap"><b>{p.title}</b><span>{p.photos.length} 순간</span></span>
          </button>
        ))}
        <button className="newbook" onClick={() => nav("/new")}><span>＋</span>새 여행</button>
      </div>
    </div>
  );
}
