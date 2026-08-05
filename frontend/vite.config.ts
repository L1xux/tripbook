import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // 폰 실기기 테스트: 터널(https) 한 개만 열고 /api를 백엔드로 넘긴다.
    // 같은 오리진이 되어야 mixed-content 없이 마이크·카메라가 열린다.
    proxy: {
      "/api": {
        target: process.env.API_TARGET ?? "http://127.0.0.1:8273",
        changeOrigin: true,
      },
    },
    allowedHosts: [".trycloudflare.com"],
  },
})
