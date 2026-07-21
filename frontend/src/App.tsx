/** 라우터: 서재(/) · 새 여행(/new) · 앨범(/p/:id). 앨범 내부(덱/그리드/책/주문)는 그 컴포넌트의 상태로 전환.
 *  누가 호출: main.tsx.
 *  무엇을 호출: screens/{Library,NewTrip,Album}. */
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Library from "./screens/Library";
import NewTrip from "./screens/NewTrip";
import Album from "./screens/Album";
import AddMoments from "./screens/AddMoments";
import Voice from "./screens/Voice";

export default function App() {
  return (
    <BrowserRouter>
      <div className="shell">
        <Routes>
          <Route path="/" element={<Library />} />
          <Route path="/new" element={<NewTrip />} />
          <Route path="/p/:id" element={<Album />} />
          <Route path="/p/:id/add" element={<AddMoments />} />
          <Route path="/v/:id" element={<Voice />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
