/** 라우터와 위자드 5단계 연결. 각 Step 컴포넌트는 steps/ 폴더에. */
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Step1Info from "./steps/Step1Info";
import Step2Photos from "./steps/Step2Photos";
import Step3Writing from "./steps/Step3Writing";
import Step4Review from "./steps/Step4Review";
import Step5Order from "./steps/Step5Order";

export default function App() {
  return (
    <BrowserRouter>
      <div className="shell">
        <Routes>
          <Route path="/" element={<Step1Info />} />
          <Route path="/p/:id/photos" element={<Step2Photos />} />
          <Route path="/p/:id/writing" element={<Step3Writing />} />
          <Route path="/p/:id/review" element={<Step4Review />} />
          <Route path="/p/:id/order" element={<Step5Order />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
