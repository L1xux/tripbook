import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // 폰 실기기 테스트용. 터널 하나만 열고 /api를 백엔드로 넘겨 같은 오리진으로 만든다.
    // 같은 오리진이라야 mixed-content 없이 마이크와 카메라가 열린다.
    proxy: {
      "/api": {
        target: process.env.API_TARGET ?? "http://localhost:8273",
        changeOrigin: true,
      },
    },
    allowedHosts: [".ts.net", ".trycloudflare.com"],
  },
})
