import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // `strictPort` لا رفاهية: المنفذ ٥١٧٣ مثبَّت في `api/app/config.py` و٢٤ ملفّ
    // اختبار خلفيّ عبر فحص `Origin` (ADR-006). فانزلاقٌ صامت إلى ٥١٧٤ يجعل
    // الخادم يردّ ٤٠٣ على **كل** طلب مغيِّر للحالة — وعطلٌ يبدو كخطأ صلاحيات.
    strictPort: true,
    // وكيل بدل CORS: في الإنتاج تكون الواجهة والـAPI على أصل واحد، فالوكيل
    // يحاكي ذلك في التطوير بدل أن نفتح أصلًا لا وجود له لاحقًا.
    proxy: { '/api': 'http://127.0.0.1:5055' },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
    typecheck: { enabled: true, include: ['src/**/*.test-d.ts'] },
  },
})
