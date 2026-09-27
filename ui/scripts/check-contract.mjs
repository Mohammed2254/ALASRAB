/*
  @covers ق-٢١٩

  تطابق العقد: كل حقلٍ عشريّ في بايثون له نوع `Decimal` في TypeScript.

  **لماذا بوابة لا ثقة؟** لأن ADR-009 يقوم كلّه على تمييزٍ بين نوعين يبدوان
  واحدًا في JSON: `"611.25"` عشريٌّ نصّيّ، و`42.2` نسبةٌ رقمية. والتمييز
  مكتوبٌ في مكانين — `api/app/schemas/*.py` و`ui/src/api/types/*.ts` — ومكانان
  يجب أن يتّفقا يتباعدان في أوّل حقلٍ يُضاف لأحدهما.

  **والانحراف صامت في اتّجاه واحد فقط، وهو الاتّجاه الخطير:** حقلٌ يُضاف إلى
  بايثون ولا يُضاف إلى TS لا يُسقط شيئًا (الشاشة لا تعرضه بعد)، ويظهر يوم
  يعرضه أحدهم رقمًا. أمّا العكس — نوعٌ في TS بلا حقل — فيُكتشَف فورًا عند أوّل
  قراءة. فالبوابة تحرس الاتّجاه الصامت.

  **والقائمة تُشتقّ حيًّا من المخطّطات لا تُكتب هنا** — قائمةٌ مكتوبة تصير
  نسخةً ثالثة تتباعد عن الاثنتين.
*/

import { readFileSync, readdirSync, existsSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const UI = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const SCHEMAS = resolve(UI, '..', 'api', 'app', 'schemas')
const TYPES = resolve(UI, 'src', 'api', 'types')

// `as_string=True` ليس أوّل معامل دائمًا (`fields.Decimal(required=True,
// as_string=True)` شائعة)، وقد يمتدّ الاستدعاء أسطرًا (`validate=...` طويل).
// الصياغة الأولى افترضت الموضع الأول والسطر الواحد، فأخفت خمسة حقول عشرية
// حقيقية (`hours_per_unit`, `multiplier`, `weight_pct`, `quantity`,
// `score_pct`) — اكتُشف بمطابقة `grep "fields.Decimal("` يدويًّا مقابل عدد
// البوابة، أوّل مرّة لمس فيها و-١٧ ملفًّا (`rules_admin.py`) لم يفحصه أحد من
// قبل (`HANDOFF.md` الدرس ٣٣). النطاق ١٦٠ حرفًا يتّسع لأطول استدعاء قائم
// (`quantity` بثلاثة أسطر) بهامش، دون الانزلاق إلى إعلان الحقل التالي.
const DECIMAL_RE = /^\s*([a-z_0-9]+)\s*=\s*fields\.Decimal\(\s*[\s\S]{0,160}?as_string\s*=\s*True/gm
const NUMERIC_RE = /^\s*([a-z_0-9]+)\s*=\s*fields\.(?:Float|Int|Integer)\(/gm

// حارس الفراغ — نفس درس `MIN_CRITERIA`: استخراجٌ دون هذا عطلٌ في الفحص لا
// نجاحٌ له (مجلّد مُعاد تسميته، أو تغيّر صيغة الإعلان في Marshmallow).
// رُفع بعد تصحيح الرجعة أعلاه ليكشف أيّ تراجع مستقبليّ فورًا؛ و١٨ في و-٢٠
// مع `hours_total` (مجموع ساعات المعاينة) — يُرفع مع كل عشريٍّ جديد.
const EXPECTED_MIN_DECIMALS = 18

function namesFrom(dir, re) {
  const found = new Map() // الاسم → الملفّات التي أعلنته
  for (const file of readdirSync(dir).filter((f) => f.endsWith('.py'))) {
    const source = readFileSync(join(dir, file), 'utf8')
    for (const [, name] of source.matchAll(re)) {
      if (!found.has(name)) found.set(name, [])
      found.get(name).push(file)
    }
  }
  return found
}

if (!existsSync(SCHEMAS)) {
  console.error(`  ❌ مجلّد المخطّطات غير موجود: ${SCHEMAS}`)
  process.exit(2)
}

const decimals = namesFrom(SCHEMAS, DECIMAL_RE)
const numerics = namesFrom(SCHEMAS, NUMERIC_RE)

if (decimals.size < EXPECTED_MIN_DECIMALS) {
  console.error(
    `  ❌ الاستخراج أعطى ${decimals.size} حقلًا عشريًّا والحدّ الأدنى ` +
      `${EXPECTED_MIN_DECIMALS} — عطلٌ في الفحص لا نجاحٌ له.`
  )
  process.exit(2)
}

let failed = 0

// ═══ ١· الاسم الواحد لا يكون عشريًّا ورقميًّا معًا ═══
// حقلٌ بالاسم نفسه يُعلَن `Decimal` في مخطّط و`Float` في آخر يجعل نوعه في TS
// كذبًا في أحد الموضعين مهما اختير — ولا يمكن للبوابة أن تحكم أيّهما.
const ambiguous = [...decimals.keys()].filter((n) => numerics.has(n))
if (ambiguous.length) {
  for (const name of ambiguous) {
    console.error(
      `  ❌ \`${name}\` مُعلَن عشريًّا في [${decimals.get(name).join(', ')}] ` +
        `ورقميًّا في [${numerics.get(name).join(', ')}]`
    )
  }
  failed += ambiguous.length
}

// ═══ ٢· كل عشريّ في بايثون له `: Decimal` في TS ═══

// أنواع `*Form` (نصف الملفّات تقريبًا) نصوصُ إدخالٍ خام قبل الإرسال — سلاسل
// نموذج عمدًا لا `Decimal`، وتحويلها الفعليّ يقع في `endpoints/*.ts` (حدّ
// الشبكة، نفس نمط `SubmitReadingForm` منذ و-١٥). **الفحص كان يتجاهلها
// بالصدفة لا بالتصميم**: يستخدم `.exec()` (أوّل تطابق فقط لا `matchAll`)
// على النص المُدمَج، فإن سبق تعريفَ الحقل في ملفّ `*Form` تعريفٌ آخر بالاسم
// نفسه صحيحًا (بترتيب قراءة الملفّات الأبجديّ) مرّ الفحص — حظّ الترتيب لا
// ضمانة. أوّل حقل بلا نظير آخر إطلاقًا (`quantity`، `AddQuranEntryForm`
// فقط) كشف الفجوة في و-١٨. تُستبعَد أجسام هذه الأنواع صراحةً بدل الاعتماد
// على ترتيب القراءة.
function stripFormTypeBodies(source) {
  const re = /export type \w*Form\b[^=]*=\s*{/g
  let out = ''
  let cursor = 0
  let match
  while ((match = re.exec(source))) {
    out += source.slice(cursor, match.index)
    let depth = 1
    let i = match.index + match[0].length
    while (depth > 0 && i < source.length) {
      if (source[i] === '{') depth++
      else if (source[i] === '}') depth--
      i++
    }
    cursor = i
    re.lastIndex = i
  }
  return out + source.slice(cursor)
}

const rawTypeSources = existsSync(TYPES)
  ? readdirSync(TYPES)
      .filter((f) => f.endsWith('.ts'))
      .map((f) => readFileSync(join(TYPES, f), 'utf8'))
      .join('\n')
  : ''
const typeSources = stripFormTypeBodies(rawTypeSources)

// الحقول التي لم تُعرَض بعد في الواجهة ليست خطأً — الواجهة تُبنى تدريجيًّا.
// فالفحص على ما **ذُكر** في TS: إن ذُكر الاسم، فكل ظهورٍ له نوعه `Decimal`.
//
// **`matchAll` لا `exec` — درسٌ ثانٍ من نفس الاكتشاف:** `exec` يعيد أوّل
// تطابق فقط، فحقلٌ يتكرّر اسمه في عدّة أنواع (`delta` في أربعة، `hours` في
// أكثر) كان يُحكَم عليه بأوّل تعريفٍ يصادفه القارئ الأبجديّ للملفّات فقط —
// لو كان صحيحًا مرّت كل التعريفات الأخرى الخاطئة بصمت. **مُثبَتٌ بالزرع:**
// `AddedQuranEntry.delta: number` لم يُكتشَف أصلًا حين كان `QuranEventRow.delta:
// Decimal` (نفس الملفّ) يسبقه أبجديًّا داخل الاستخراج.
function allDeclaredTypesOf(name, source) {
  const re = new RegExp(`\\b${name}\\??\\s*:\\s*([A-Za-z<>\\[\\]| ]+)`, 'g')
  return [...source.matchAll(re)].map((m) => m[1].trim())
}

const mistyped = []
for (const name of decimals.keys()) {
  for (const type of allDeclaredTypesOf(name, typeSources)) {
    if (!/\bDecimal\b/.test(type)) mistyped.push(`${name} → ${type}`)
  }
}
if (mistyped.length) {
  for (const m of mistyped) console.error(`  ❌ حقلٌ عشريّ بنوعٍ غير \`Decimal\`: ${m}`)
  failed += mistyped.length
}

// ═══ ٣· ولا رقميّ يُكتب `Decimal` خطأً ═══
const overtyped = []
for (const name of numerics.keys()) {
  for (const type of allDeclaredTypesOf(name, typeSources)) {
    if (/\bDecimal\b/.test(type)) overtyped.push(`${name} → ${type}`)
  }
}
if (overtyped.length) {
  for (const o of overtyped) console.error(`  ❌ حقلٌ رقميّ كُتب \`Decimal\`: ${o}`)
  failed += overtyped.length
}

if (failed) {
  console.error('\nالعقد واحدٌ في طرفين: ما يخرج نصًّا من بايثون يدخل نصًّا إلى TypeScript.')
  process.exit(1)
}

const covered = [...decimals.keys()].filter((n) => allDeclaredTypesOf(n, typeSources).length > 0)
console.log(
  `\n✅ العقد متطابق — ${decimals.size} حقلًا عشريًّا في بايثون ` +
    `(${covered.length} منها مُعرَّف في الواجهة حتى الآن) · ${numerics.size} حقلًا رقميًّا · صفر التباس.`
)
