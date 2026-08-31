/*
  @covers ق-١٣, ق-١٤, ق-١٥, ق-١٦

  فحص بصري **مقيس** في متصفّح حقيقي — لا لقطات تُنظَر بالعين وحدها.

  **لماذا لا تكفي اختبارات DOM هنا؟** أثبت Part 5 ذلك عمليًّا: رمز `⛔` مرّ في
  ستة عشر اختبارًا **وظهر مربّعًا فارغًا في المتصفّح** لأن الخطوط مستضافة محليًّا
  بلا خطّ إيموجي. **وجود العنصر في DOM ليس دليل ظهوره ولا قابليته للاستعمال.**

  الإطار **٣٧٥px بالضبط** كما ينصّ `SLICE-01` §٨: أصغر عرض شائع، وما يمرّ عليه
  يمرّ على ما فوقه.
*/
import { chromium } from 'playwright'

const OUT = process.argv[2] ?? '/tmp'
const BASE = process.env.QA_BASE ?? 'http://localhost:5173'
const VIEWPORT = { width: 375, height: 812 }
const MIN_TOUCH = 44
const MIN_CONTRAST = 4.5
/*
  أدنى انزياح عن حافّة الإطار.

  **٨px حدٌّ أرضيّ لا اختيار تصميم** (تصميمنا يستعمل ١٦): نصٌّ ملاصق للحافّة
  يُقصّ على الأجهزة ذات الزوايا المستديرة والمناطق الآمنة، ويصعب لمسه.

  أُضيف بعد أن **مرّ فحصُ التمرير الأفقي على مخالفة حقيقية**: شاشة الدخول كانت
  بلا حشوة أفقية، فلامس العنوان والنصّ الحافّتين — و`scrollWidth` لم يتجاوز
  `clientWidth` لأن الملاصقة لا تزيد العرض. لكل فحص عمى، وهذا كان عماه.
*/
const MIN_EDGE_INSET = 8

const STUDENTS = [
  ['1001', 'normal', 'رصيد متوسّط'],
  ['1002', 'empty', 'لا أحداث'],
  ['1003', 'max', 'أعلى رتبة'],
  ['1004', 'grounded', 'أرضي'],
]

const failures = []
const fail = (criterion, detail) => failures.push(`${criterion}: ${detail}`)

/*
  القياسات تُنفَّذ داخل الصفحة: `getComputedStyle` و`getBoundingClientRect` لا
  تُقرأ إلا من سياق المتصفّح، وقراءتها من الخارج تعني تخمين ما رسمه المحرّك.
*/
const MEASURE = () => {
  const ARABIC = /[؀-ۿ]/
  const INTERACTIVE = 'button, a[href], input, select, textarea, [role="button"]'

  // نسبية الإضاءة و نسبة التباين — WCAG 2.1 §1.4.3.
  const channel = (c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)
  const luminance = ([r, g, b]) =>
    0.2126 * channel(r / 255) + 0.7152 * channel(g / 255) + 0.0722 * channel(b / 255)
  const parse = (css) => (css.match(/[\d.]+/g) ?? []).slice(0, 4).map(Number)

  // الخلفية الفعلية: العنصر قد يكون شفّافًا، فتُورَّث من أوّل سلف غير شفّاف.
  const backgroundOf = (el) => {
    for (let node = el; node; node = node.parentElement) {
      const bg = parse(getComputedStyle(node).backgroundColor)
      if (bg.length >= 3 && (bg[3] === undefined || bg[3] > 0.5)) return bg.slice(0, 3)
    }
    return [0, 0, 0]
  }

  const contrast = (fg, bg) => {
    const [a, b] = [luminance(fg), luminance(bg)].sort((x, y) => y - x)
    return (a + 0.05) / (b + 0.05)
  }

  const out = { overflow: null, touch: [], spacing: [], contrast: [], edges: [] }

  // ق-١٣ — تمرير أفقي.
  const doc = document.documentElement
  out.overflow = { scrollWidth: doc.scrollWidth, clientWidth: doc.clientWidth }

  // ق-١٣ب — نصٌّ ملاصق لحافّة الإطار. يُفحص حاملُ النصّ المباشر وحده: الحاويات
  // تمتدّ بعرض الشاشة بحقّ، والمقصوص هو الحرف لا الصندوق.
  const vw = doc.clientWidth
  for (const el of document.querySelectorAll('body *')) {
    const own = [...el.childNodes]
      .filter((n) => n.nodeType === Node.TEXT_NODE && n.textContent.trim())
      .map((n) => n.textContent)
      .join('')
    if (!own.trim()) continue
    const r = el.getBoundingClientRect()
    if (r.width === 0) continue
    out.edges.push({ text: own.trim().slice(0, 26), left: Math.round(r.left), right: Math.round(r.right), vw })
  }

  // ق-١٤ — هدف اللمس المرسوم.
  for (const el of document.querySelectorAll(INTERACTIVE)) {
    const r = el.getBoundingClientRect()
    if (r.width === 0 && r.height === 0) continue // غير مرئي: لا يُلمس أصلًا
    out.touch.push({
      tag: el.tagName.toLowerCase(),
      label: (el.getAttribute('aria-label') ?? el.id ?? el.textContent ?? '').trim().slice(0, 30),
      w: Math.round(r.width),
      h: Math.round(r.height),
    })
  }

  /*
    ق-١٥ — يُفحص **المحتوى لا الصنف**.

    عنصرٌ يحمل `tracking-[0.3em]` وليس فيه حرف عربي سليم: الأرقام لا تتّصل.
    والفحص بالصنف يسقطه كذبًا. نأخذ النصّ المباشر للعنصر (لا نصّ أبنائه) حتى
    لا يُنسب تباعدُ حاوٍ إلى محتوى ابنٍ لا يحمله.
  */
  for (const el of document.querySelectorAll('body *')) {
    const own = [...el.childNodes]
      .filter((n) => n.nodeType === Node.TEXT_NODE)
      .map((n) => n.textContent)
      .join('')
    if (!ARABIC.test(own)) continue
    const ls = getComputedStyle(el).letterSpacing
    const px = ls === 'normal' ? 0 : parseFloat(ls)
    if (px > 0.01) out.spacing.push({ text: own.trim().slice(0, 30), letterSpacing: ls })
  }

  // ق-١٦ — تباين محسوب من الألوان المرسومة، لا منقول من وثيقة.
  for (const el of document.querySelectorAll('body *')) {
    const own = [...el.childNodes]
      .filter((n) => n.nodeType === Node.TEXT_NODE && n.textContent.trim())
      .map((n) => n.textContent)
      .join('')
    if (!own.trim()) continue
    const style = getComputedStyle(el)
    const fg = parse(style.color).slice(0, 3)
    const ratio = contrast(fg, backgroundOf(el))
    out.contrast.push({
      text: own.trim().slice(0, 26),
      size: style.fontSize,
      ratio: Math.round(ratio * 100) / 100,
    })
  }
  return out
}

async function audit(page, label) {
  const m = await page.evaluate(MEASURE)

  if (m.overflow.scrollWidth > m.overflow.clientWidth) {
    fail('ق-١٣', `${label}: تمرير أفقي — ${m.overflow.scrollWidth}px داخل ${m.overflow.clientWidth}px`)
  }
  for (const e of m.edges) {
    if (e.left < MIN_EDGE_INSET || e.right > e.vw - MIN_EDGE_INSET) {
      fail('ق-١٣', `${label}: «${e.text}» ملاصق للحافّة [${e.left} → ${e.right}] في ${e.vw}px`)
    }
  }
  for (const t of m.touch) {
    if (t.w < MIN_TOUCH || t.h < MIN_TOUCH) {
      fail('ق-١٤', `${label}: «${t.label}» ${t.w}×${t.h} < ${MIN_TOUCH}`)
    }
  }
  for (const s of m.spacing) {
    fail('ق-١٥', `${label}: «${s.text}» letter-spacing=${s.letterSpacing} على نصّ عربي`)
  }
  for (const c of m.contrast) {
    if (c.ratio < MIN_CONTRAST) {
      fail('ق-١٦', `${label}: «${c.text}» (${c.size}) تباين ${c.ratio}:1 < ${MIN_CONTRAST}`)
    }
  }

  const worst = m.contrast.reduce((a, b) => (a.ratio <= b.ratio ? a : b), { ratio: Infinity })
  const smallest = m.touch.reduce(
    (a, b) => (Math.min(a.w, a.h) <= Math.min(b.w, b.h) ? a : b),
    { w: Infinity, h: Infinity, label: '—' },
  )
  // أدنى انزياح فعليّ عن أقرب حافّة. تُحسب من القائمة مباشرةً: مُراكمٌ ابتدائيّ
  // مصطنع يفوز على القيم الحقيقية ويعرض رقمًا كاذبًا.
  const insets = m.edges.map((e) => Math.min(e.left, e.vw - e.right))
  const tightestInset = insets.length ? Math.min(...insets) : '—'
  console.log(
    `  ${label.padEnd(18)} عرض ${m.overflow.scrollWidth}/${m.overflow.clientWidth} · ` +
      `أدنى انزياح ${tightestInset}px · ` +
      `أصغر لمس ${smallest.w}×${smallest.h} · أدنى تباين ${worst.ratio}:1 · ` +
      `تباعد عربي ${m.spacing.length}`,
  )
}

const browser = await chromium.launch()
console.log(`\n═══ قياس على ${VIEWPORT.width}px ═══`)

for (const [studentNo, slug, label] of STUDENTS) {
  const ctx = await browser.newContext({ viewport: VIEWPORT, deviceScaleFactor: 2, locale: 'ar' })
  const page = await ctx.newPage()
  const consoleErrors = []
  page.on('pageerror', (e) => consoleErrors.push(String(e)))

  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.fill('#student_no', studentNo)
  await page.fill('#pin', '1234')
  await page.click('button[type=submit]')
  await page.waitForSelector('text=بطاقة الطيار', { timeout: 8000 })
  await page.waitForTimeout(600)
  await page.screenshot({ path: `${OUT}/deck-${slug}.png`, fullPage: true })
  await audit(page, label)
  if (consoleErrors.length) fail('صفحة', `${label}: ${consoleErrors.join(' | ')}`)
  await ctx.close()
}

// شاشة الدخول وحالة خطئها — أوّل ما يراه الطالب.
const ctx = await browser.newContext({ viewport: VIEWPORT, deviceScaleFactor: 2, locale: 'ar' })
const page = await ctx.newPage()
await page.goto(BASE, { waitUntil: 'networkidle' })
await page.screenshot({ path: `${OUT}/login.png`, fullPage: true })
await audit(page, 'شاشة الدخول')

await page.fill('#student_no', '9999')
await page.fill('#pin', '0000')
await page.click('button[type=submit]')
await page.waitForSelector('[role=alert]')
await page.screenshot({ path: `${OUT}/login-error.png`, fullPage: true })
await audit(page, 'خطأ الدخول')
await browser.close()

if (failures.length) {
  console.error(`\n❌ ${failures.length} مخالفة:`)
  for (const f of failures) console.error(`   ${f}`)
  process.exit(1)
}
console.log('\n✅ ق-١٣ · ق-١٤ · ق-١٥ · ق-١٦ — مقيسة ومجتازة.')
