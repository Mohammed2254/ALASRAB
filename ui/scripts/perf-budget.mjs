/*
  @covers ق-٢٢٤, ق-٢٢٥, ق-٢٣١

  ميزانية الأداء — حجمان مضغوطان مستقلّان، مقاسان لا مقدَّران.

  **يقيس بنفسه لا يثق بمخرَج `vite build` النصّي.** ذاك يطبع تقريبًا
  للعرض البشريّ (قد يقرّب أو يُقصّ)؛ هنا `zlib.gzipSync` على البايتات
  الفعلية لكل ملفّ في `dist/assets/`، فالرقم حجّةٌ لا وصفٌ.

  **سقفان مستقلّان لا سقفٌ مشترك** (`و-١٣.md` سجلّ نقطة تفتيش ٣، `HANDOFF.md`
  §٠): JS ≤١٦٥KB · CSS ≤٢٢KB. دمجُهما في رقم واحد كان سيسمح لـCSS متضخّم
  أن يختبئ خلف فائضٍ في ميزانية JS، والعكس.

  **يُشغَّل بعد `npx vite build` لا بدلًا منه** — نفس ترتيب `visual-qa.mjs`
  بعد الخادمين: هذا السكربت يقرأ `dist/` القائم، ولا يبنيه.

  **ملاحظة مُتحقَّقة:** رقم هذا السكربت يختلف عن رقم `vite build` النصّي
  (هنا JS ≈٦٩KB، هناك «gzip: 71.34 kB») **على نفس البايتات الخام حرفيًّا**
  (٢٢٦٥٧٧ بايت في الحالتين، مؤكَّد بـ`ls -la`) — استُبعدت وحدة عشرية/ثنائية
  (`kB`/`KiB`) وBrotli بديلًا صريحًا كتفسيرين محتملين وكلاهما لا يطابق. لم
  يُحسَم السبب الدقيق داخل `vite`، ولا حاجة له: هذا السكربت يقيس **البايتات
  المكتوبة فعليًّا على القرص** بـ`zlib.gzipSync` القياسيّ — وهو الرقم الحاكم
  لما يصل المتصفّح، لا تقدير أداة بناء داخليّ.
*/

import { gzipSync } from 'node:zlib'
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { dirname, extname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const UI = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const ASSETS_DIR = resolve(UI, 'dist/assets')

// حارس الفراغ: بناءٌ لم يقع (أو `dist/` قديم من تشغيلة أخرى) يجب أن يُبلَّغ
// عنه بصوت عالٍ، لا أن يمرّ الفحص على قائمة فارغة فيبدو "لا شيء تجاوز
// السقف" وهو في الحقيقة "لا شيء قِيس أصلًا" (نفس درس `MIN_CRITERIA`).
if (!existsSync(ASSETS_DIR)) {
  console.error(`  ❌ ${ASSETS_DIR} غير موجود — شغّل \`npx vite build\` أوّلًا. هذا عطلٌ في الفحص لا نجاحٌ له.`)
  process.exit(2)
}

const files = readdirSync(ASSETS_DIR)
if (files.length === 0) {
  console.error(`  ❌ ${ASSETS_DIR} فارغ — بناءٌ ناقص. عطلٌ في الفحص لا نجاحٌ له.`)
  process.exit(2)
}

const KB = 1024
const BUDGETS = {
  '.js': { label: 'JS', capBytes: 165 * KB },
  '.css': { label: 'CSS', capBytes: 22 * KB },
}

const totals = { '.js': 0, '.css': 0 }
for (const file of files) {
  const ext = extname(file)
  if (!(ext in BUDGETS)) continue
  const bytes = readFileSync(resolve(ASSETS_DIR, file))
  totals[ext] += gzipSync(bytes).length
}

let failed = 0
for (const [ext, { label, capBytes }] of Object.entries(BUDGETS)) {
  const used = totals[ext]
  const usedKB = (used / KB).toFixed(2)
  const capKB = (capBytes / KB).toFixed(0)
  if (used > capBytes) {
    const overKB = ((used - capBytes) / KB).toFixed(2)
    console.error(`  ❌ ${label}: ${usedKB}KB مضغوطة > السقف ${capKB}KB — فائضٌ ${overKB}KB`)
    failed++
  } else {
    console.log(`  ✅ ${label}: ${usedKB}KB مضغوطة / السقف ${capKB}KB`)
  }
}

if (failed) {
  console.error('\nالميزانية اسمٌ بلا فرض إن لم تُقَس: عدِّل الحزمة أو ارفع السقف بقرار موثَّق، لا صمتًا.')
  process.exit(1)
}
console.log('\n✅ البناء تحت السقفين معًا.')
