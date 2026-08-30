import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // وكيل بدل CORS: في الإنتاج تكون الواجهة والـAPI على أصل واحد، فالوكيل
    // يحاكي ذلك في التطوير بدل أن نفتح أصلًا لا وجود له لاحقًا.
    // والأصل الواحد يجعل المتصفّح يرسل Origin: http://localhost:5173 مع كل
    // طلب مغيِّر للحالة — وهو ما يقبله فحص ADR-006 في الخادم.
    proxy: { '/api': 'http://127.0.0.1:5055' },
  },
  test: { environment: 'jsdom', globals: true, setupFiles: './src/test/setup.js' },
})
