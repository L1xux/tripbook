/** 화면 라우팅. 앨범 안의 덱과 그리드, 책, 주문은 라우트가 아니라 Album의 상태로 전환한다.
 *  누가 호출: main.tsx.
 *  무엇을 호출: screens의 Library와 NewTrip, Album, AddMoments, Voice. */
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
