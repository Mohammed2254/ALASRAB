/*
  @covers ق-١١, ق-٢٥, ق-٣٠, ق-٣٨

  فحص معماري: **الواجهة تعرض ولا تحسب** (`AGENTS.md` ٥).

  يفحص شجرة البناء لا النصّ: بحث نصّي عن «400» يطابق تعليقًا أو صنف Tailwind،
  وشجرةُ البناء لا تطابق إلا رقمًا حقيقيًّا في تعبير حقيقي.

  ما يمنعه:
    · مقارنة (`hours >= 400`) — عتبة رتبة في الواجهة.
      **والمنع شامل عمدًا:** عتبةٌ لا تُكتب إلا بمقارنة، فحظرها كلّها يجعل
      المخالفة مستحيلة بلا اجتهاد في التمييز. وثمنه أن `list.length > 0` تُكتب
      `list.length ? …` — كلفة سطر مقابل قاعدة بلا ثغرات.
    · عملية حسابية (`x / y * 100`) — نسبة تقدّم تُحسب هنا.
    · رقم من أرقام المجال حرفيًّا — عتبة أو وزن أو مهلة «أرضي».

  ولو انكسر أحدها لتباعدت نسختا القاعدة، فرأى الطالب رتبةً في بطاقته وأخرى في
  لوحة الصدارة — والثقة في الأرقام هي المنتج كلّه.
*/
import { readFileSync } from 'node:fs'
import { Parser } from 'acorn'
import jsx from 'acorn-jsx'

const JsxParser = Parser.extend(jsx())

/*
  فئتان، لكلٍّ خطرها:

  · **مستهلكات العقد** ترى الساعات والنسبة والحالة، فتستطيع إعادة اشتقاقها.
    تُمنع من كل مقارنة وعملية حسابية ورقم مجال.

  · **البدائيات البصرية** ترسم SVG بإحداثيات، فحسابها هندسة لا قاعدة. والخطر
    فيها مختلف: أن تلمس حقلًا من حقول المجال أصلًا. تُمنع من ذكرها بالاسم.
*/
const CONTRACT_CONSUMERS = [
  'src/pages/PilotDeck.jsx',
  'src/pages/Login.jsx',
  // و-٤ (ق-٢٥): الشاشتان تستهلكان عقد القراءة — `hours` تصل محسوبة من الحدث،
  // ولا تُشتقّ هنا من `pages × وزن`.
  'src/pages/MyReadings.jsx',
  'src/pages/admin/ReadingQueue.jsx',
  'src/pages/admin/Report.jsx',
]
const VISUAL_PRIMITIVES = ['src/components/Insignia.jsx', 'src/components/Placard.jsx']

// حقول المجال في ردّ `/me/deck`. البدائية البصرية لا تراها إطلاقًا.
const DOMAIN_FIELDS = /\b(hours|at_hours|progress_pct|remaining|grounded|last_activity_on|rank_in_org)\b/
// عتبات الرتب · مهلة «أرضي» · أوزان الأنشطة · مضاعفات الإتقان.
const DOMAIN_NUMBERS = new Set([400, 900, 1500, 14, 2.5, 0.6, 0.15, 3.0, 1.5, 0.5])
const COMPARISONS = new Set(['<', '>', '<=', '>='])
const ARITHMETIC = new Set(['*', '/', '%'])

function inspect(file) {
  const ast = JsxParser.parse(readFileSync(file, 'utf8'), {
    ecmaVersion: 'latest',
    sourceType: 'module',
  })
  const hits = { comparisons: [], arithmetic: [], numbers: [] }

  ;(function walk(node) {
    if (!node || typeof node !== 'object') return
    if (node.type === 'BinaryExpression') {
      if (COMPARISONS.has(node.operator)) hits.comparisons.push(node.operator)
      if (ARITHMETIC.has(node.operator)) hits.arithmetic.push(node.operator)
    }
    if (node.type === 'Literal' && DOMAIN_NUMBERS.has(node.value)) hits.numbers.push(node.value)
    for (const key of Object.keys(node)) {
      const value = node[key]
      if (Array.isArray(value)) value.forEach(walk)
      else if (value && typeof value === 'object' && value.type) walk(value)
    }
  })(ast)

  return hits
}

let failed = 0
for (const file of CONTRACT_CONSUMERS) {
  const { comparisons, arithmetic, numbers } = inspect(file)
  const problems = [
    comparisons.length && `مقارنات (${comparisons.join(' ')})`,
    arithmetic.length && `عمليات حسابية (${arithmetic.join(' ')})`,
    numbers.length && `أرقام مجال (${numbers.join(', ')})`,
  ].filter(Boolean)

  if (problems.length) {
    console.error(`  ❌ ${file} → ${problems.join(' · ')}`)
    failed++
  } else {
    console.log(`  ✅ ${file}`)
  }
}

for (const file of VISUAL_PRIMITIVES) {
  const source = readFileSync(file, 'utf8')
  const touched = source.match(DOMAIN_FIELDS)
  if (touched) {
    console.error(`  ❌ ${file} → يلمس حقل مجال: ${touched[0]}`)
    failed++
  } else {
    console.log(`  ✅ ${file} (بدائية بصرية — لا تلمس حقلًا من حقول المجال)`)
  }
}

if (failed) {
  console.error('\nالواجهة تعرض ولا تحسب: القرار يملكه الخادم، وهنا تُعرض نتيجته.')
  process.exit(1)
}
console.log('\n✅ لا قاعدة عمل في الواجهة.')
