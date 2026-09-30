import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // البيان يُمكّن `perf-budget` من التمييز بين **حزمة الإقلاع** وما يُحمَّل
  // بتأجيل: بدونه يجمع الملفّات كلّها في رقمٍ واحد فيعاقب التقسيمَ بدل أن
  // يكافئه (زيادةُ بضع مئات من البايتات لبنية الأجزاء).
  build: { manifest: true },
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
  // نفس وكيل التطوير لخادم المعاينة — **المعاينة تخدم البناء الحقيقيّ**
  // بأجزائه المقسَّمة، وهي الطريقة الوحيدة لإثبات ما يُنزَّل فعلًا على الشبكة
  // (خادم التطوير يقدّم وحداتٍ لا حِزمًا، فلا يُقاس عليه التقسيم).
  preview: {
    port: 4173,
    strictPort: true,
    proxy: { '/api': 'http://127.0.0.1:5055' },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
    typecheck: { enabled: true, include: ['src/**/*.test-d.ts'] },
  },
})
