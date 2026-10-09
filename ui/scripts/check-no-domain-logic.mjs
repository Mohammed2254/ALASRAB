/*
  @covers ق-٢١٢, ق-٢١٣, ق-٢٢٦, ق-٢٢٨

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
  لا تمثّله. ويحرس هذا الاستثناءَ فحصان.

  **الأوّل — `gsap` لا تُستورَد خارج `motion/` إطلاقًا** (بلا استثناء لـ`ui/`):
  الاعتمادية بحجمها وتشابكها الزمنيّ تبقى محصورة تمامًا (`ADR-007`)، والبدائية
  التي تحتاج حركةً تستدعي `motion/mo.ts` لا تكتب GSAP بنفسها.

  **والثاني — `motion/geometry` لا تُستورَد خارج `motion/` **و**`ui/`** (لا
  خارجهما معًا). **تصحيحٌ لقاعدة و-١٣ الأصلية** (كانت تمنع الاستيراد خارج
  `motion/` بلا استثناء) — التنفيذ الفعليّ في و-١٤ كشف أنها كانت تمنع
  الاستهلاك المقصود نفسه: البدائيات البصرية (`FuelDial`, `FormationSky`,
  `ProgressBar`, `ChgBadge`) **مهمّتها تحويل نسبةٍ إلى شكل**، وهذا **هو**
  استهلاك `geometry` الشرعيّ لا تسريبًا منه. أمّا `screens/**` فتبقى ممنوعة:
  الشاشة تمرّر نسبةً وصلتها من الخادم إلى بدائية جاهزة، ولا تحسب شكلًا بنفسها
  أبدًا — فبقاء المنع هناك هو جوهر «الواجهة تعرض ولا تحسب» (`AGENTS.md` ٥).
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
// **تُشتقّ بالنمط لا تُسرَد بيدٍ** (و-٢٢): كانت قائمةً يدوية بثمانيةٍ
// وعشرين ملفًّا **مطابقةً حرفيًّا** لـ`src/ui/**/*.tsx` الواقع سطرًا واحدًا
// فوقها — أي صيانةُ نسخةٍ ثانية من نمطٍ موجود. وثمنُها دُفع ثلاث مرّات في
// و-٢٠ و-٢١ (بدائيةٌ تُضاف فتُنسى من القائمة، أو تُحذف فتبقى معلَنة).
//
// وحارسُ «معلَنٌ وغير موجود» أدناه يبقى: هو الآن يحرس خطأ القراءة لا خطأ
// السرد، ولا يُستغنى عنه — فحصٌ يصمت على ملفٍّ لا يُقرأ فحصٌ أعمى.
const VISUAL_PRIMITIVES = globSync('src/ui/**/*.tsx', { cwd: UI }).sort()
const MOTION_ONLY = 'src/motion/'

// حارس الفراغ: أقلّ عددٍ معقول من الملفّات المفحوصة. استخراجٌ دونه **عطلٌ في
// الفحص لا نجاحٌ له** — يُرفَع مع نموّ الواجهة، ولا يُخفَّض لتمرير بناء.
const EXPECTED_MIN = 1

// حقول المجال في ردّ `/me/deck`. البدائية البصرية لا تراها إطلاقًا.
const DOMAIN_FIELDS =
  /\b(hours|at_hours|progress_pct|remaining|grounded|last_activity_on|rank_in_org)\b/
// عتبات الرتب · مهلة «أرضي» · أوزان الأنشطة · مضاعفات الإتقان.
//
// **و`3.0` أُسقِطت من القائمة في و-٢١، ولا تُعاد.** السبب أن جافاسكربت لا
// تملك إلا نوعًا رقميًّا واحدًا: `3.0 === 3`، فالمدخل يُمسك **كلّ عددٍ صحيح
// قيمته ثلاثة** — خانةَ خيارٍ، وعمودَ شبكة، وعدّ صفوف. وقد وقع ذلك فعلًا على
// `SLOTS = [1, 2, 3, 4]` في نموذج سؤال اليوم: مخالفةٌ مُبلَّغٌ عنها ولا
// مخالفة فيها.
//
// **وإسقاطُها لا يفتح ثغرةً ذات معنى:** الحارسُ الحقيقيّ ضدّ حساب الساعات في
// الشاشة هو منعُ الحساب نفسه — `ARITHMETIC` و`BANNED_CALLEES` أدناه. ورقمُ
// ٣ عاريًا بلا ضربٍ ولا قسمةٍ ولا `Number()` **لا يحسب شيئًا**، وبقيّة
// القائمة إمّا كسورٌ مميَّزة (٢.٥ · ٠.٦ · ٠.١٥ · ١.٥ · ٠.٥) أو أعدادٌ لا
// تقع عرَضًا (٤٠٠ · ٩٠٠ · ١٥٠٠ · ١٤).
//
// **والدرس أهمّ من البند:** بوّابةٌ تُنذر كاذبًا يحتال عليها من يصطدم بها —
// فيُسمّي الثابتَ باسمٍ آخر أو يُخرجه من الملفّ، ويبقى الاسم ويضيع الحرس.
// وهذه ثالث مرّة في هذا المشروع تُصاب فيها بوّابةٌ بما وُجدت لتمنعه (الدرسان
// ٣٣ و٣٥، وتعليقُ و-٢٠ الذي خدع فحصَ نقطة الكسر).
const DOMAIN_NUMBERS = new Set([400, 900, 1500, 14, 2.5, 0.6, 0.15, 1.5, 0.5])
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

// حارسا الاستثناء: `gsap` مسموحةٌ في `motion/` وحده — وإلّا سُرّبت اعتماديةٌ
// قرارُها محصورٌ عمدًا (ADR-007). و`geometry` مسموحةٌ في `motion/` **و**`ui/`
// معًا — تحويل نسبةٍ إلى شكل هو مهمّة البدائية البصرية نفسها، لا تسريبًا
// منها (أعلاه). و`src/test/` مُستثنًى من كليهما: استيرادٌ اختباريّ للفحص
// المباشر لا حسابٌ في شاشة.
const TEST_ONLY = 'src/test/'
const UI_ONLY = 'src/ui/'
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

const geometryLeaks = ALL_SOURCE.filter((rel) => !rel.startsWith(UI_ONLY)).filter((rel) =>
  /from\s+['"][^'"]*motion\/geometry['"]/.test(readFileSync(resolve(UI, rel), 'utf8'))
)
if (geometryLeaks.length) {
  console.error(`  ❌ استيراد \`motion/geometry\` خارج \`motion/\`/\`ui/\`: ${geometryLeaks.join(' · ')}`)
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
