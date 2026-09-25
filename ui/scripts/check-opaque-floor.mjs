/*
  @covers ق-٢١٤, ق-٢١٥, ق-٢١٦

  ثلاث قواعد لونية تُفرَض على المصدر قبل أن يفرضها المتصفّح.

  **لماذا قبل المتصفّح؟** لأن `visual-qa.mjs` حين لا يجد أرضية معتمة تحت نصّ
  **يُرجع سقوطًا لا تخطّيًا**، ورسالته «تعذّر قياس تباينه» — وهي رسالةٌ تُقرأ
  كعطلِ أداةٍ فتُكتَم أو يُلتفّ عليها، لا كعيبٍ في الشاشة. فالبوابة هنا تقول
  **ماذا يُفعَل** لا «تعذّر».

  والنموذج المعتمد يحمل **١٣ تدرّجًا** بلا `background-color` — كلٌّ منها
  سقوطٌ مؤكَّد لو نُقل كما هو. فهذه البوابة ليست احتياطًا بل استجابةٌ لعيبٍ
  مقيس (`VISUAL.md §٢.٢`).

  ويفحص **المصدر لا المبنيّ**: الرسالة يجب أن تسمّي الملفّ والسطر الذي يكتبه
  الإنسان، لا سطرًا في حزمةٍ مولَّدة.
*/

import { readFileSync, globSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const UI = resolve(dirname(fileURLToPath(import.meta.url)), '..')

const TOKENS_FILE = 'src/styles/tokens.css'
const SCANNED = ['src/**/*.css', 'src/**/*.tsx', 'src/**/*.ts']
const EXPECTED_MIN = 2 // حارس الفراغ — نفس درس `MIN_CRITERIA`

const HEX = /#[0-9a-fA-F]{3,8}\b/
const GRADIENT = /(linear|radial|conic)-gradient\s*\(/
const BACKDROP = /backdrop-filter\s*:/
const OPAQUE_BG = /background-color\s*:\s*var\(--color-(bg|bg-2|surface|surface-2)\)/
const LINE_AS_TEXT = /(^|[^-\w])color\s*:\s*var\(--color-line\)/

const files = SCANNED.flatMap((p) => globSync(p, { cwd: UI })).sort()

if (files.length < EXPECTED_MIN) {
  console.error(
    `  ❌ الجمع أعطى ${files.length} ملفًّا والحدّ الأدنى ${EXPECTED_MIN} — ` +
      'عطلٌ في الفحص لا نجاحٌ له.'
  )
  process.exit(2)
}

let failed = 0

for (const rel of files) {
  const source = readFileSync(resolve(UI, rel), 'utf8')
  const lines = source.split('\n')

  // ═══ ق-٢١٥ — صفر لون حرفيّ خارج ملفّ الرموز ═══
  if (rel !== TOKENS_FILE) {
    lines.forEach((line, i) => {
      // التعليقات لا تُحاسَب: توثيق القيمة المقيسة بجوار الرمز مفيد لا مخالفة.
      const code = line.split('/*')[0].split('//')[0]
      const hex = HEX.exec(code)
      if (hex) {
        console.error(
          `  ❌ ${rel}:${i + 1} → لون حرفيّ \`${hex[0]}\` خارج \`${TOKENS_FILE}\`. ` +
            'أضفه رمزًا في `@theme` واستعمله بـ`var(--color-…)`.'
        )
        failed++
      }
    })
  }

  // ═══ ق-٢١٦ — `--color-line` لا يحمل نصًّا ═══
  lines.forEach((line, i) => {
    if (LINE_AS_TEXT.test(line)) {
      console.error(
        `  ❌ ${rel}:${i + 1} → \`--color-line\` في \`color:\` ونسبته ٢٫٤٦٢:١. ` +
          'استعمل `--color-text-dim` للنصّ الثانوي.'
      )
      failed++
    }
  })

  // ═══ ق-٢١٤ — كل تدرّج/ضبابية تعلن أرضية معتمة ═══
  // الفحص على مستوى كتلة القاعدة `{ … }`: التدرّج وأرضيته قد يفترقان سطورًا.
  for (const [, body] of source.matchAll(/\{([^{}]*)\}/g)) {
    if ((GRADIENT.test(body) || BACKDROP.test(body)) && !OPAQUE_BG.test(body)) {
      const offender = (GRADIENT.exec(body) ?? BACKDROP.exec(body))[0]
      const at = lines.findIndex((l) => l.includes(offender.slice(0, 12)))
      console.error(
        `  ❌ ${rel}:${at + 1} → \`${offender}\` بلا أرضية معتمة في القاعدة نفسها. ` +
          'أضف `background-color: var(--color-surface)` (أو bg/bg-2/surface-2) ' +
          'وإلّا عجز قياس التباين — وعجزُه سقوطٌ لا تخطٍّ.'
      )
      failed++
    }
  }
}

if (failed) {
  console.error('\nاللون يُقاس لا يُقدَّر: نصٌّ بلا أرضية معتمة نصٌّ بلا نسبة.')
  process.exit(1)
}
console.log(`\n✅ اللوحة منضبطة (${files.length} ملفًّا مفحوصًا).`)
