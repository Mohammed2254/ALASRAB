/*
  @covers ق-٢٤٢

  عُرفُ نقطة الكسر الواحدة، محروسًا بالقياس لا بالعُرف.

  `tokens.css` يمحو سلّم Tailwind بـ`--breakpoint-*: initial` ويُعلن واحدة فقط
  (`desk` عند ١٠٢٤px، مطابقةً لـ`SCOPE.md §١٣`: قائمة جانبية وجداول فوقها،
  وبطاقات مكدَّسة تحتها).

  **لماذا بوابة؟** لأن عيب المحو أنّ بادئةً مجهولة **تُصدِر لا شيء صامتةً**:
  `md:hidden` تبقى في `className` ولا تُنتج قاعدةً، فتبدو الشاشة سليمةً في
  المراجعة ومكسورةً عند المقاس. مُثبَتٌ حيًّا في و-٢٠: `md:flex` و`lg:block` لم
  تُنتجا حرفًا واحدًا في CSS المبنيّ، بينما أنتجت `desk:hidden` قاعدةً واحدة
  داخل `@media (width>=1024px)`.

  **ولماذا هنا لا في Vitest؟** جُرِّب أوّلًا كاختبار وحدة، فسقط مرّتين لسببين
  حقيقيَّين: `node:fs` يُلزم `@types/node` في `tsconfig.json` الذي يُعلن
  `types` صراحةً فيسقط `tsc --noEmit`؛ و`import.meta.glob(... '?raw')` يُرجع
  **نصًّا فارغًا لملفّات CSS** لأن Vitest يُعطّل معالجة CSS افتراضيًّا — أي
  تأكيدٌ يمرّ على فراغ. وفحصُ عُرفٍ في ملفّات المصدر مكانه مع البوابات الثلاث
  الأخرى أصلًا.

  **والصيغة الحديثة لا القديمة:** Tailwind 4 يُصدِر `@media (width>=1024px)` لا
  `min-width:`، ففحص المُخرَج بحثًا عن `min-width` يمرّ دائمًا بلا أن يقيس شيئًا.
  فالفحص على المصدر.
*/

import { readFileSync, readdirSync } from 'node:fs'
import { dirname, join, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const UI = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const SRC = join(UI, 'src')

// سلّم Tailwind الافتراضي الممحوّ — أيّ بادئة منه تُصدِر لا شيء.
// **وهذا الفحص وحده يبقى صارمًا حتى داخل التعليقات** — نفس عُرف فحص المفردات
// في `check-no-domain-logic.mjs`: بادئةٌ مذكورة في تعليقٍ تُنسَخ إلى كودٍ
// عاجلًا أو آجلًا، والتكلفة كلمةٌ تُعاد صياغتها لا عطلٌ يُطارَد.
const WIPED_PREFIX = /\b(sm|md|lg|xl|2xl):[a-z[]/
const DECLARED_BREAKPOINT = /--breakpoint-([a-z0-9]+)\s*:/g
// الإعلان لا ذِكرُه: `--breakpoint-*: initial` **في بداية سطرٍ وينتهي بفاصلة
// منقوطة**. مُثبَتٌ بالزرع في و-٢٠: `includes('--breakpoint-*: initial')` كان
// يطابق **تعليق `tokens.css` الشارح نفسه**، فحذفُ الإعلان الفعليّ مرّ بـ✅ —
// بوابةٌ خُدِعت بتوثيقها.
const WIPE_DECLARATION = /^\s*--breakpoint-\*\s*:\s*initial\s*;/m

/**
 * تجريد تعليقات الكتلة `/* … *\/`.
 *
 * ضروريّ في الاتّجاهين معًا، وكلاهما مُثبَتٌ بالزرع: تعليقٌ يذكر إعلانًا
 * مطلوبًا يجعل غيابَه يمرّ، وتعليقٌ يذكر مخالفةً يجعل حضورَه يسقط.
 */
const stripBlockComments = (source) => source.replace(/\/\*[\s\S]*?\*\//g, '')

function sources(dir) {
  const out = []
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name)
    if (entry.isDirectory()) out.push(...sources(path))
    else if (/\.(ts|tsx|css)$/.test(entry.name)) out.push(path)
  }
  return out
}

const files = sources(SRC)

// حارس الفراغ — نفس درس `MIN_CRITERIA` و`EXPECTED_MIN_DECIMALS`: استخراجٌ
// فارغ عطلٌ في الفحص لا نجاحٌ له (مجلّد مُعاد تسميته، أو امتدادٌ تغيّر).
const EXPECTED_MIN_FILES = 40
if (files.length < EXPECTED_MIN_FILES) {
  console.error(
    `  ❌ الاستخراج أعطى ${files.length} ملفًّا والحدّ الأدنى ${EXPECTED_MIN_FILES} — ` +
      'عطلٌ في الفحص لا نجاحٌ له.'
  )
  process.exit(2)
}

let failed = 0
const rel = (path) => relative(SRC, path)

// ═══ ١· لا بادئة من السلّم الممحوّ ═══
for (const file of files) {
  const source = readFileSync(file, 'utf8')
  const lines = source.split('\n')
  lines.forEach((line, index) => {
    const hit = WIPED_PREFIX.exec(line)
    if (!hit) return
    console.error(
      `  ❌ ${rel(file)}:${index + 1} → \`${hit[0]}\` بادئةٌ من السلّم الممحوّ، ` +
        'فلا تُصدِر قاعدةً واحدة. البديل الوحيد المعلَن: `desk:` (١٠٢٤px).'
    )
    failed++
  })
}

// ═══ ٢· نقطة كسر واحدة معلَنة، والمحو صريح ═══
const tokens = stripBlockComments(readFileSync(join(SRC, 'styles', 'tokens.css'), 'utf8'))
if (!WIPE_DECLARATION.test(tokens)) {
  console.error(
    '  ❌ `tokens.css` بلا `--breakpoint-*: initial` — سلّم Tailwind كامل يعود، ' +
      'فتتسلّل `md:`/`xl:` بلا قرار منتج.'
  )
  failed++
}
const declared = [...tokens.matchAll(DECLARED_BREAKPOINT)].map((m) => m[1])
if (declared.length !== 1 || declared[0] !== 'desk') {
  console.error(
    `  ❌ نقاط الكسر المعلَنة [${declared.join(', ')}] — يُتوقَّع \`desk\` وحدها ` +
      '(`SCOPE.md §١٣`: حدٌّ واحد لا سلّم).'
  )
  failed++
}
if (!tokens.includes('--breakpoint-desk: 1024px')) {
  console.error('  ❌ `--breakpoint-desk` ليس ١٠٢٤px — يخالف `SCOPE.md §١٣` حرفيًّا.')
  failed++
}

// ═══ ٣· احتياطيّ `useDesk` يطابق الرمز ═══
// `useDesk.ts` يقرأ `--breakpoint-desk` من `:root` حيًّا، ولجسدوم احتياطيٌّ
// مكتوب. ورقمان يعنيان الشيء نفسه في موضعين يتباعدان — فيُربطان هنا.
const deskSource = readFileSync(join(SRC, 'ui', 'useDesk.ts'), 'utf8')
const fallback = /const FALLBACK = '([^']+)'/.exec(stripBlockComments(deskSource))
if (!fallback) {
  console.error('  ❌ `useDesk.ts` بلا `FALLBACK` — تعذّر ربطه بالرمز.')
  failed++
} else if (!tokens.includes(`--breakpoint-desk: ${fallback[1]}`)) {
  console.error(
    `  ❌ احتياطيّ \`useDesk\` (${fallback[1]}) لا يطابق ` +
      '`--breakpoint-desk` في `tokens.css` — رقمٌ واحد في موضعين تباعدا.'
  )
  failed++
}

// ═══ ٤· لا استعلام وسائط بيدٍ خارج `base.css`، وذاك لتقليل الحركة وحده ═══
for (const file of files) {
  const source = stripBlockComments(readFileSync(file, 'utf8'))
  if (!source.includes('@media (')) continue
  const queries = [...source.matchAll(/@media \(([^)]*)\)/g)].map((m) => m[1].trim())
  if (rel(file) === join('styles', 'base.css')) {
    const unexpected = queries.filter((q) => q !== 'prefers-reduced-motion: reduce')
    for (const q of unexpected) {
      console.error(
        `  ❌ styles/base.css → \`@media (${q})\` — الأساس لتقليل الحركة وحده. ` +
          'التخطيط الثاني يُكتب ببادئة `desk:` فيُقاس ويُحصر في مكان واحد.'
      )
      failed++
    }
    continue
  }
  for (const q of queries) {
    console.error(
      `  ❌ ${rel(file)} → \`@media (${q})\` مكتوبٌ بيد. البديل: بادئة \`desk:\`، ` +
        'فتبقى نقطة الكسر رمزًا واحدًا في `tokens.css` لا رقمًا مبثوثًا.'
    )
    failed++
  }
}

if (failed) {
  console.error('\nنقطةُ كسرٍ واحدة قرارُ منتجٍ مُصادَق، لا عادةً تُنسَخ من إطار عمل.')
  process.exit(1)
}
console.log(
  `\n✅ الاستجابة منضبطة — نقطة كسر واحدة (desk ١٠٢٤px)، ${files.length} ملفًّا مفحوصًا.`
)
