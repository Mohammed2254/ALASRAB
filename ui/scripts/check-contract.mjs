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

const DECIMAL_RE = /^\s*([a-z_0-9]+)\s*=\s*fields\.Decimal\(as_string=True/gm
const NUMERIC_RE = /^\s*([a-z_0-9]+)\s*=\s*fields\.(?:Float|Int|Integer)\(/gm

// حارس الفراغ — نفس درس `MIN_CRITERIA`: استخراجٌ دون هذا عطلٌ في الفحص لا
// نجاحٌ له (مجلّد مُعاد تسميته، أو تغيّر صيغة الإعلان في Marshmallow).
const EXPECTED_MIN_DECIMALS = 10

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
const typeSources = existsSync(TYPES)
  ? readdirSync(TYPES)
      .filter((f) => f.endsWith('.ts'))
      .map((f) => readFileSync(join(TYPES, f), 'utf8'))
      .join('\n')
  : ''

// الحقول التي لم تُعرَض بعد في الواجهة ليست خطأً — الواجهة تُبنى تدريجيًّا.
// فالفحص على ما **ذُكر** في TS: إن ذُكر الاسم، فنوعه يجب أن يكون `Decimal`.
const mistyped = []
for (const name of decimals.keys()) {
  const declared = new RegExp(`\\b${name}\\??\\s*:\\s*([A-Za-z<>\\[\\]| ]+)`).exec(typeSources)
  if (declared && !/\bDecimal\b/.test(declared[1])) {
    mistyped.push(`${name} → ${declared[1].trim()}`)
  }
}
if (mistyped.length) {
  for (const m of mistyped) console.error(`  ❌ حقلٌ عشريّ بنوعٍ غير \`Decimal\`: ${m}`)
  failed += mistyped.length
}

// ═══ ٣· ولا رقميّ يُكتب `Decimal` خطأً ═══
const overtyped = []
for (const name of numerics.keys()) {
  const declared = new RegExp(`\\b${name}\\??\\s*:\\s*([A-Za-z<>\\[\\]| ]+)`).exec(typeSources)
  if (declared && /\bDecimal\b/.test(declared[1])) {
    overtyped.push(`${name} → ${declared[1].trim()}`)
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

const covered = [...decimals.keys()].filter((n) => new RegExp(`\\b${n}\\??\\s*:`).test(typeSources))
console.log(
  `\n✅ العقد متطابق — ${decimals.size} حقلًا عشريًّا في بايثون ` +
    `(${covered.length} منها مُعرَّف في الواجهة حتى الآن) · ${numerics.size} حقلًا رقميًّا · صفر التباس.`
)
