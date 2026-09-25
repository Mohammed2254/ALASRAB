/*
  @covers ق-٢١٢, ق-٢١٣

  فحص معماري: **الواجهة تعرض ولا تحسب** (`AGENTS.md` ٥).

  منقولٌ عن `web/scripts/check-no-domain-logic.mjs` بقواعده كما هي — والقواعد
  هي الجوهر لا المحلّل: عتبات الرتب وأوزان الأنشطة ومهلة «أرضي» لم تتغيّر،
  لأن عقد الخلفية لم يتغيّر.

  **ما تغيّر شيئان، وكلاهما إصلاحُ عطبٍ في الأصل لا تفضيلٌ:**

  ١· **المحلّل.** `acorn-jsx` لا يقرأ TSX إطلاقًا، فكان الفحص سيمرّ على كل
     ملفّ لأنه لا يفهمه لا لأنه نظيف — وهو أسوأ أنواع الخضرة.
     البديل `@typescript-eslint/typescript-estree` اختير لأنه **يُخرِج أشكال
     عُقَد ESTree نفسها** (`BinaryExpression` · `Literal`)، فالماشي أدناه هو
     ماشي الأصل حرفيًّا ولا يُبطَل إثباته العدائيّ المتراكم (١٤ معيارًا).
     و`typescript` الرسميّ مرفوض هنا: يستعمل `SyntaxKind` فيوجب إعادة كتابة
     الماشي — أي إبطال الإثبات لا نقله.

  ٢· **الجمع بـglob لا بقائمة يدوية.** الأصل يحمل ٢٨ مسارًا مكتوبًا، وملفٌّ
     ناقص فيه **ينهار** بـ`ENOENT` بدل أن يُبلّغ، وشاشةٌ جديدة لا تُفحَص حتى
     يتذكّر أحدٌ إضافتها. والقائمة التي تعتمد على التذكّر ليست بوابة.
     وحارس `EXPECTED_MIN` يمنع النقيض: glob يعطي صفرًا (نمطٌ خاطئ، مجلّد
     مُعاد تسميته) فيمرّ الفحص على لا شيء — نفس درس `MIN_CRITERIA` في بوابة
     الشرائح، ونفس الدرس ٥.

  **وما لا يُفحَص هنا بقصد موثَّق:** `src/motion/**` — فيه كل الحساب الهندسيّ
  (قوس العدّاد · زاوية العقرب · إحداثيات التشكيل). وهندسةُ رسمٍ ليست قاعدة
  عمل: لا تقرّر رتبةً ولا عتبةً ولا وزنًا، ولا يمكن أن تتباعد عن الخادم لأنها
  لا تمثّله. ويحرس هذا الاستثناءَ فحصان: `geometry` لا تُستورَد خارج `motion/`،
  و`gsap` كذلك لا تُستورَد خارج `motion/` (كلاهما أدناه، و-١٤ أضافت الثاني —
  `ADR-007` نصّ عليه وقت اعتماد الاعتمادية لا وقت أوّل استعمال فعليّ لها).
*/

import { readFileSync } from 'node:fs'
import { globSync } from 'node:fs'
import { dirname, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { parse } from '@typescript-eslint/typescript-estree'

// المسارات تُحلّ من موضع السكربت لا من `process.cwd()` — تشغيلُه من جذر
// المستودع كان ينهار في الأصل بـ`ENOENT` على أوّل ملفّ.
const UI = resolve(dirname(fileURLToPath(import.meta.url)), '..')

const CONSUMER_GLOBS = ['src/screens/**/*.tsx', 'src/ui/**/*.tsx']
const VISUAL_PRIMITIVES = ['src/ui/HexIcon.tsx', 'src/ui/TierBadge.tsx']
const MOTION_ONLY = 'src/motion/'

// حارس الفراغ: أقلّ عددٍ معقول من الملفّات المفحوصة. استخراجٌ دونه **عطلٌ في
// الفحص لا نجاحٌ له** — يُرفَع مع نموّ الواجهة، ولا يُخفَّض لتمرير بناء.
const EXPECTED_MIN = 1

// حقول المجال في ردّ `/me/deck`. البدائية البصرية لا تراها إطلاقًا.
const DOMAIN_FIELDS =
  /\b(hours|at_hours|progress_pct|remaining|grounded|last_activity_on|rank_in_org)\b/
// عتبات الرتب · مهلة «أرضي» · أوزان الأنشطة · مضاعفات الإتقان.
const DOMAIN_NUMBERS = new Set([400, 900, 1500, 14, 2.5, 0.6, 0.15, 3.0, 1.5, 0.5])
const COMPARISONS = new Set(['<', '>', '<=', '>='])
// `**` أُضيف على الأصل: الأسّ عمليةٌ حسابية كغيره، وغيابه ثغرةٌ لا قرار.
const ARITHMETIC = new Set(['*', '/', '%', '**'])
// دوالٌّ تُنتج رقمًا من نصّ أو تحسب — ممنوعة في الشاشة، مسموحة في `motion/`.
const BANNED_CALLEES = new Set(['Number', 'parseFloat', 'parseInt'])

function inspect(file) {
  const source = readFileSync(file, 'utf8')
  const ast = parse(source, { jsx: true, loc: false, range: false })
  const hits = { comparisons: [], arithmetic: [], numbers: [], callees: [] }

  ;(function walk(node) {
    if (!node || typeof node !== 'object') return
    if (node.type === 'BinaryExpression') {
      if (COMPARISONS.has(node.operator)) hits.comparisons.push(node.operator)
      if (ARITHMETIC.has(node.operator)) hits.arithmetic.push(node.operator)
    }
    if (node.type === 'Literal' && DOMAIN_NUMBERS.has(node.value)) hits.numbers.push(node.value)
    if (node.type === 'CallExpression') {
      const callee = node.callee
      if (callee?.type === 'Identifier' && BANNED_CALLEES.has(callee.name)) {
        hits.callees.push(callee.name)
      }
      if (callee?.type === 'MemberExpression' && callee.object?.name === 'Math') {
        hits.callees.push(`Math.${callee.property?.name ?? '?'}`)
      }
    }
    for (const key of Object.keys(node)) {
      const value = node[key]
      if (Array.isArray(value)) value.forEach(walk)
      else if (value && typeof value === 'object' && value.type) walk(value)
    }
  })(ast)

  return { hits, source }
}

const consumers = CONSUMER_GLOBS.flatMap((pattern) => globSync(pattern, { cwd: UI })).sort()

if (consumers.length < EXPECTED_MIN) {
  console.error(
    `  ❌ الجمع أعطى ${consumers.length} ملفًّا والحدّ الأدنى ${EXPECTED_MIN} — ` +
      'هذا عطلٌ في الفحص لا نجاحٌ له (نمطٌ خاطئ أو مجلّد مُعاد تسميته).'
  )
  process.exit(2)
}

let failed = 0

for (const rel of consumers) {
  const { hits } = inspect(resolve(UI, rel))
  const problems = [
    hits.comparisons.length && `مقارنات (${hits.comparisons.join(' ')})`,
    hits.arithmetic.length && `عمليات حسابية (${hits.arithmetic.join(' ')})`,
    hits.numbers.length && `أرقام مجال (${hits.numbers.join(', ')})`,
    hits.callees.length && `دوالّ حساب (${hits.callees.join(', ')})`,
  ].filter(Boolean)

  if (problems.length) {
    console.error(`  ❌ ${rel} → ${problems.join(' · ')}`)
    failed++
  } else {
    console.log(`  ✅ ${rel}`)
  }
}

for (const rel of VISUAL_PRIMITIVES) {
  const path = resolve(UI, rel)
  let source
  try {
    source = readFileSync(path, 'utf8')
  } catch {
    // ملفٌّ مُعلَن وغير موجود **يُبلَّغ عنه** ولا يُنهي العملية — الأصل كان
    // ينهار هنا، فيبدو العطل خطأ بيئة لا نتيجة فحص.
    console.error(`  ❌ ${rel} → بدائية بصرية معلَنة وغير موجودة`)
    failed++
    continue
  }
  const touched = source.match(DOMAIN_FIELDS)
  if (touched) {
    console.error(`  ❌ ${rel} → يلمس حقل مجال: ${touched[0]}`)
    failed++
  } else {
    console.log(`  ✅ ${rel} (بدائية بصرية — لا تلمس حقلًا من حقول المجال)`)
  }
}

// حارس الاستثناء: `geometry` و`gsap` مسموحتان هنا وحده، فلا تُستورَدان خارج
// `motion/` — وإلّا صار الباب الخلفيّ يُخرج الحساب من البوابة (`geometry`)
// أو يُسرّب اعتماديةً قرارُها محصورٌ عمدًا (`gsap`، ADR-007). والمسح على
// شجرة المصدر كلّها خارج `motion/` لا على أدلّة "المستهلكين" وحدها — القيد
// معماريّ لا خاصّ بطبقة الشاشات. و`src/test/` مُستثنى: اختبار وحدة يستورد
// الدالّة **ليفحصها** لا ليحسب بها في شاشة — استيرادٌ شرعيّ لا تسريب.
const TEST_ONLY = 'src/test/'
const ALL_SOURCE = globSync('src/**/*.{ts,tsx}', { cwd: UI }).filter(
  (rel) => !rel.startsWith(MOTION_ONLY) && !rel.startsWith(TEST_ONLY)
)

if (ALL_SOURCE.length < EXPECTED_MIN) {
  console.error(
    `  ❌ مسح شجرة المصدر أعطى ${ALL_SOURCE.length} ملفًّا والحدّ الأدنى ${EXPECTED_MIN} — ` +
      'عطلٌ في الفحص لا نجاحٌ له.'
  )
  process.exit(2)
}

const geometryLeaks = ALL_SOURCE.filter((rel) =>
  /from\s+['"][^'"]*motion\/geometry['"]/.test(readFileSync(resolve(UI, rel), 'utf8'))
)
if (geometryLeaks.length) {
  console.error(`  ❌ استيراد \`motion/geometry\` خارج \`motion/\`: ${geometryLeaks.join(' · ')}`)
  failed++
}

const gsapLeaks = ALL_SOURCE.filter((rel) =>
  /from\s+['"]gsap['"]/.test(readFileSync(resolve(UI, rel), 'utf8'))
)
if (gsapLeaks.length) {
  console.error(`  ❌ استيراد \`gsap\` خارج \`motion/\` (ADR-007): ${gsapLeaks.join(' · ')}`)
  failed++
}

if (failed) {
  console.error('\nالواجهة تعرض ولا تحسب: القرار يملكه الخادم، وهنا تُعرض نتيجته.')
  process.exit(1)
}
console.log(`\n✅ لا قاعدة عمل في الواجهة (${consumers.length} ملفًّا مفحوصًا).`)
