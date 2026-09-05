/*
  @covers ق-١٣, ق-١٤, ق-١٥, ق-١٦, ق-٢٦, ق-٣١, ق-٣٩, ق-٤٥, ق-٦٤, ق-٧٧, ق-٩٢, ق-١٠٦, ق-١٢٢, ق-١٣٨

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
  /*
    المتصفّح يعيد الألوان **بصيغتين مختلفتي المدى**، وخلطهما كان عمى الأداة:
    `rgb(10, 12, 16)` و`rgba(...)` بمدى **0–255**، بينما Chromium يعيد كل لون
    ذي شفافية (وهو ما تولّده `bg-apron/78` في Tailwind) بصيغة
    `color(srgb 0.078 0.098 0.133 / 0.78)` بمدى **0–1**.

    قسمةُ الثانية على 255 كانت تجعل اللوح **أسود شبه نقيّ** — وهو أفضل خلفية
    ممكنة لنصّ فاتح — فتُبلَّغ نسبٌ أعلى من الحقيقة بمعامل ثابت 1.159، ويمرّ
    ما كان يجب أن يسقط. أُثبت عمليًّا: نصّ `#797979` نسبته الحقيقية 4.16:1
    عبر البوابة وقد أُبلغ 4.82:1.

    واسم فضاء اللون يُنزَع أوّلًا: `display-p3` يحمل رقمًا في اسمه فيلوّث
    الالتقاط لو التُقطت الأرقام من النصّ كما هو.
  */
  const parse = (css) => {
    const s = String(css).trim()
    const open = s.indexOf('(')
    if (open < 0) return [] // 'transparent' أو اسم لوني — لا قنوات
    const unit = s.startsWith('color(')
    const body = s.slice(open + 1, s.lastIndexOf(')')).replace(unit ? /^\s*[a-z0-9-]+\s+/i : /^$/, '')
    const nums = (body.match(/[\d.]+/g) ?? []).map(Number)
    if (nums.length < 3) return []
    const rgb = nums.slice(0, 3).map((v) => (unit ? v * 255 : v))
    return nums.length > 3 ? [...rgb, nums[3]] : rgb
  }

  /*
    الخلفية الفعلية = **تركيب** الطبقات لا أوّل طبقة «كافية».

    الصيغة السابقة كانت تقبل أوّل سلف شفافيته > 0.5 وتعامله كأنه معتم، فتُهمل
    ما تحته. واللوح عندنا 0.78 فوق الأسفلت، وتركيبهما `#12161E` — وهو الرقم
    الذي توثّقه `VISUAL.md`. فالتركيب هنا ليس تدقيقًا زائدًا بل هو ما يجعل
    الرقم المقيس مساويًا للرقم الموثَّق.
  */
  const backgroundOf = (el) => {
    const layers = []
    for (let node = el; node; node = node.parentElement) {
      const c = parse(getComputedStyle(node).backgroundColor)
      if (c.length < 3) continue
      const alpha = c.length > 3 ? c[3] : 1
      if (alpha <= 0) continue
      layers.push([c[0], c[1], c[2], alpha])
      if (alpha >= 0.999) break
    }
    // بلا أرضية معتمة لا يوجد رقم صادق. والافتراض الصامت (أسود) يرفع النسبة
    // ويُمرّر المخالفة — وهو الفخّ نفسه، فيُعلَن العجز بدل تخمينه (الدرس ٥).
    if (!layers.length || layers[layers.length - 1][3] < 0.999) return null
    let out = layers[layers.length - 1].slice(0, 3)
    for (let i = layers.length - 2; i >= 0; i--) {
      const [r, g, b, a] = layers[i]
      out = [r, g, b].map((v, k) => a * v + (1 - a) * out[k])
    }
    return out
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
    const bg = backgroundOf(el)
    // عجزٌ مُعلَن لا مُخمَّن: نصٌّ بلا أرضية معتمة تحته لا نسبة صادقة له.
    const ratio = fg.length < 3 || bg === null ? null : contrast(fg, bg)
    out.contrast.push({
      text: own.trim().slice(0, 26),
      size: style.fontSize,
      ratio: ratio === null ? null : Math.round(ratio * 100) / 100,
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
    if (c.ratio === null) {
      fail('ق-١٦', `${label}: «${c.text}» (${c.size}) تعذّر قياس تباينه — لا أرضية معتمة تحته`)
    } else if (c.ratio < MIN_CONTRAST) {
      fail('ق-١٦', `${label}: «${c.text}» (${c.size}) تباين ${c.ratio}:1 < ${MIN_CONTRAST}`)
    }
  }

  const measured = m.contrast.filter((c) => c.ratio !== null)
  const worst = measured.reduce((a, b) => (a.ratio <= b.ratio ? a : b), { ratio: Infinity })
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

  /*
    ق-٢٦ — شاشتا و-٤ تُقاسان كبقيّتها.

    ولا يكفي فحصهما لطالب واحد: «قراءاتي» تُقاس على من له طلبات بالحالات الثلاث
    (سالم)، و«الطابور» لا يُفتح إلا لمشرف (بندر). فحصُ شاشةٍ فارغة لا يثبت أن
    محتواها يُعرض صحيحًا.
  */
  if (slug === 'empty') {
    await page.click('text=قراءاتي')
    await page.waitForSelector('text=تسجيل قراءة', { timeout: 8000 })
    await page.waitForTimeout(500)
    await page.screenshot({ path: `${OUT}/my-readings.png`, fullPage: true })
    await audit(page, 'قراءاتي')
  }
  if (slug === 'normal') {
    await page.click('text=التقرير الدوري')
    await page.waitForSelector('text=الأسبوع', { timeout: 8000 })
    await page.waitForTimeout(500)
    await page.screenshot({ path: `${OUT}/report.png`, fullPage: true })
    await audit(page, 'التقرير الدوري')
    await page.click('text=رجوع')
    await page.waitForSelector('text=بطاقة الطيار', { timeout: 8000 })

    await page.click('text=طابور القراءات')
    await page.waitForSelector('text=طابور القراءات', { timeout: 8000 })
    await page.waitForTimeout(500)
    await page.screenshot({ path: `${OUT}/reading-queue.png`, fullPage: true })
    await audit(page, 'طابور القراءات')
    await page.click('text=رجوع')
    await page.waitForSelector('text=بطاقة الطيار', { timeout: 8000 })

    /*
      و-٧ (ق-٦٤) — أربع شاشات جديدة. `getByRole('button', ...)` لا `text=` هنا:
      عنوان شاشة الأسراب وزرّ فتحها يحملان النصّ نفسه، فيتنازع محدِّد نصّي عام.
    */
    for (const [label, slugPart] of [
      ['الأوزان', 'weights'],
      ['العتبات', 'thresholds'],
      ['الأسراب', 'teams'],
      ['سجلّ التغييرات', 'audit'],
      ['محطة التزوّد', 'station'],
      ['أنشطة الوقود', 'fuel-activities'],
      ['تقييم نشاط', 'fuel-assess'],
      // و-٩ب (ق-٩٢) — لوحتا الصدارة ومشهد التشكيل.
      ['صدارة الأفراد', 'pilots-board'],
      ['صدارة الأسراب', 'teams-board'],
      ['مشهد التشكيل', 'formation'],
      // و-٩ج (ق-١٠٦) — سؤال اليوم.
      ['سؤال اليوم', 'question'],
      // و-٩د (ق-١٢٢) — طيار الأسبوع والملاحظات.
      ['طيار الأسبوع', 'week-pilot'],
      ['أرسل ملاحظة', 'submit-note'],
      ['الملاحظات', 'notes'],
      ['اختيار طيار الأسبوع', 'choose-week-pilot'],
      // و-٩هـ (ق-١٣٨) — الحضور.
      ['الحضور', 'attendance'],
    ]) {
      await page.getByRole('button', { name: label, exact: true }).click()
      await page.waitForSelector(`h1:has-text("${label}")`, { timeout: 8000 })
      await page.waitForTimeout(500)
      await page.screenshot({ path: `${OUT}/admin-${slugPart}.png`, fullPage: true })
      await audit(page, label)
      await page.click('text=رجوع')
      await page.waitForSelector('text=بطاقة الطيار', { timeout: 8000 })
    }
  }

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
console.log('\n✅ ق-١٣ · ق-١٤ · ق-١٥ · ق-١٦ · ق-٢٦ · ق-٣١ · ق-٩٢ · ق-١٠٦ · ق-١٢٢ · ق-١٣٨ — مقيسة ومجتازة.')
