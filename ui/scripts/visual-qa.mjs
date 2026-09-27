/*
  @covers ق-٢١٧, ق-٢٢٠, ق-٢٢١, ق-٢٢٢, ق-٢٢٣, ق-٢٤٤

  القياس البصريّ الحيّ لواجهة `ui/` — في متصفّح حقيقي، لا في jsdom.

  **والسائق أبسط من سائق `web/` بفارقٍ بنيويّ:** ذاك يتنقّل بسلسلة نقرات على
  سلاسل عربية حرفية (`text=رجوع` ثمانِ مرّات)، فإعادةُ تسمية زرٍّ واحد تكسر
  عشرين شاشة. وهنا لكل شاشة **مسارٌ حقيقيّ** (ADR-008)، فالتنقّل `page.goto`
  — أسرع، وأعزل، ولا يعتمد على نصّ زرّ.

  **ويقيس عند ثلاثة مقاسات** لا واحد (`SCOPE.md §١٣` بعد تصحيح و-١٣):
  ٣٢٠px أضيق جوّال حقيقيّ · ٣٧٥px الأساس · ١٢٨٠px حيث تظهر تخطيطات المشرف.
  والقياس عند مقاس واحد كان يجعل «مستجيب» ادّعاءً لا قياسًا.
*/

import { chromium } from 'playwright'

import { audit, failures, MEASURE } from './qa-core.mjs'

const OUT = process.argv[2] ?? '/tmp'
const BASE = process.env.QA_BASE ?? 'http://localhost:5173'

// ثلاثة مقاسات: الأضيق الحقيقيّ · الأساس · حيث يعمل المشرف.
const VIEWPORTS = [
  { width: 320, height: 720, slug: '320', label: '٣٢٠px أضيق جوّال' },
  { width: 375, height: 812, slug: '375', label: '٣٧٥px الأساس' },
  { width: 1280, height: 800, slug: '1280', label: '١٢٨٠px سطح المكتب' },
  // ١٤٤٠px هو المقاس الذي يسمّيه النموذج المعتمد للوحة المشرف حرفيًّا
  // («لوحة المشرف — 1440px»)، وأُضيف في و-٢٠ مع القشرة الإدارية. والارتفاع
  // ٨٠٠px مقصود: القائمة الجانبية أطول منه (≈٩٩٠px) فيُقاس تمريرها الداخليّ
  // فعلًا بدل أن يتّسع المنفذ فيخفي الحاجة إليه.
  { width: 1440, height: 800, slug: '1440', label: '١٤٤٠px لوحة المشرف' },
]

const PIN = '1234'
const STUDENT = '1001'

// الشاشات المبنيّة حتى الآن — تنمو مع كل شريحة، ولا تُحذف منها شاشة بلا سبب.
const SCREENS = [
  { path: '/', slug: 'deck', label: 'البطاقة' },
  { path: '/readings', slug: 'readings', label: 'قراءاتي' },
  { path: '/station', slug: 'station', label: 'محطة التزوّد' },
  { path: '/formation', slug: 'formation', label: 'مشهد التشكيل' },
  { path: '/board', slug: 'board', label: 'الصدارة' },
  { path: '/tahdir', slug: 'tahdir', label: 'تحضير القراءة' },
  { path: '/question', slug: 'question', label: 'سؤال اليوم' },
  { path: '/week-pilot', slug: 'week-pilot', label: 'طيار الأسبوع' },
  { path: '/note', slug: 'note', label: 'ملاحظة' },
  { path: '/admin', slug: 'admin-dashboard', label: 'لوحة القيادة' },
  { path: '/admin/report', slug: 'admin-report', label: 'التقرير' },
  { path: '/admin/queue', slug: 'admin-queue', label: 'طابور القراءات' },
  { path: '/admin/tahdir', slug: 'admin-tahdir-queue', label: 'طابور تحضير القراءة' },
  { path: '/admin/tahdir/report', slug: 'admin-tahdir-report', label: 'تقرير تحضير القراءة' },
  { path: '/admin/teams', slug: 'admin-teams', label: 'الأسراب' },
  { path: '/admin/weights', slug: 'admin-weights', label: 'الأوزان' },
  { path: '/admin/thresholds', slug: 'admin-thresholds', label: 'العتبات' },
  { path: '/admin/notes', slug: 'admin-notes', label: 'الملاحظات' },
  { path: '/admin/week-pilot', slug: 'admin-week-pilot', label: 'اختيار طيار الأسبوع' },
  { path: '/admin/audit', slug: 'admin-audit', label: 'الصندوق الأسود' },
  { path: '/admin/fuel/activities', slug: 'admin-fuel-activities', label: 'أنشطة الوقود' },
  { path: '/admin/fuel/assess', slug: 'admin-fuel-assess', label: 'تقييم نشاط' },
  { path: '/admin/attendance', slug: 'admin-attendance', label: 'الحضور' },
  { path: '/admin/quran', slug: 'admin-quran-edit', label: 'التصحيح والتعديل القرآني' },
  { path: '/admin/rasd', slug: 'admin-rasd-import', label: 'استيراد راصد' },
]

async function measureAt(browser, viewport) {
  const ctx = await browser.newContext({
    viewport: { width: viewport.width, height: viewport.height },
    deviceScaleFactor: 2,
    locale: 'ar',
  })
  const page = await ctx.newPage()
  page.on('pageerror', (err) => failures.push(`صفحة: خطأ JS غير ملتقَط — ${err.message}`))

  // ═══ شاشة الدخول: تُقاس قبل الدخول، وهي الشاشة الوحيدة التي يراها زائر ═══
  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.waitForSelector('#student_no', { timeout: 8000 })
  await audit(page, `الدخول · ${viewport.label}`)
  await page.screenshot({ path: `${OUT}/login-${viewport.slug}.png`, fullPage: true })

  /*
    ق-٢٢٢ — الخطّ المحمَّل هو **الخطّ المرسوم**، لا خطٌّ مُعلَن في CSS.

    والفحص على **ما يُرسَم فعلًا** لا على وزنٍ نظنّه مستعملًا: أوّل صياغة هنا
    سألت عن `800 26px Almarai` بينما العنوان يُرسَم بوزن الجسم، فأبلغت عن
    «سقوطٍ إلى خطّ النظام» وهو سليم. الفحص الذي يخمّن ما يُرسَم يكذب في
    الاتّجاهين — ولذلك يُقرأ هنا `getComputedStyle` ثم يُسأل عنه بعينه.

    **وثانية صياغة أُثبتت عمياء أيضًا (نقطة تفتيش ٤، انظر §٨.٢):**
    `document.fonts.check(spec)` **لا** يتطلّب الوزن المطلوب بالضبط — خوارزمية
    مطابقة CSS القياسية تستبدل صامتةً أقرب وزنٍ **محمَّل في العائلة نفسها**
    (٧٠٠ حين يُطلَب ٨٠٠ مثلًا)، فتُرجع `true` رغم غياب الوزن المطلوب حرفيًّا —
    ومُثبَت بحذف وزن Almarai/800 العربي فعليًّا: النتيجة `check()==true` دائمًا.
    فالفحص هنا **يقرأ `document.fonts` مباشرةً** ويطابق العائلة والوزن حرفًا
    بحرف على وجه لا اسمًا — لا مطابقةً تقريبية تُخفي غياب الوجه بالضبط.
  */
  const fontReport = await page.evaluate(async () => {
    // **الانتظار قبل السؤال:** خطٌّ سليمٌ لم يصل بعد يبدو غائبًا. وبلا هذا
    // السطر يصير الفحص سباقًا مع الشبكة، فيحمرّ أحيانًا ويخضرّ أحيانًا على
    // الكود نفسه — وهو أسوأ من فحصٍ لا يوجد.
    await document.fonts.ready
    const unq = (s) => s.replace(/^["']|["']$/g, '')
    const loaded = [...document.fonts].filter((f) => f.status === 'loaded')
    const out = []
    for (const el of document.querySelectorAll('h1, h2, p, label, button')) {
      const text = (el.textContent ?? '').trim()
      if (!text) continue // عنصرٌ بلا نصّ مرسوم لا خطّ له يُقاس
      const cs = getComputedStyle(el)
      const family = unq(cs.fontFamily.split(',')[0].trim())
      const weight = cs.fontWeight
      const exact = loaded.some((f) => unq(f.family) === family && f.weight === weight)
      if (!exact) out.push({ family, weight, size: cs.fontSize, tag: el.tagName, text: text.slice(0, 20) })
    }
    return out
  })
  for (const miss of fontReport) {
    failures.push(
      `ق-٢٢٢: <${miss.tag}> «${miss.text}» (${miss.size}) بوزن ${miss.weight} — ` +
        `لا وجه محمَّل لعائلة «${miss.family}» بهذا الوزن بالضبط`
    )
  }

  // ═══ ق-٢٢٢ب — صفر إيموجي في النصّ المعروض (درس `⛔` في و-١) ═══
  const emoji = await page.evaluate(() => {
    const re = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE0F}]/u
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
    const found = []
    let node
    while ((node = walker.nextNode())) {
      if (re.test(node.textContent ?? '')) found.push(node.textContent.trim().slice(0, 40))
    }
    return found
  })
  if (emoji.length) {
    failures.push(`ق-٢٢٢: محرف إيموجي في النصّ — ${emoji.join(' · ')} (يجب أن يكون SVG)`)
  }

  // ═══ الدخول ثم الشاشات المحميّة ═══
  await page.fill('#student_no', STUDENT)
  await page.fill('#pin', PIN)
  await page.click('button[type=submit]')
  await page.waitForFunction(() => !document.querySelector('#student_no'), { timeout: 8000 })

  for (const screen of SCREENS) {
    await page.goto(BASE + screen.path, { waitUntil: 'networkidle' })
    await audit(page, `${screen.label} · ${viewport.label}`)
    await page.screenshot({ path: `${OUT}/${screen.slug}-${viewport.slug}.png`, fullPage: true })
  }

  await ctx.close()
}

/*
  ق-٢٢٠ · ق-٢٢١ — ضمانةُ زرّ أندرويد **مقيسةً لا منويّة**، بنقرٍ حقيقيّ على
  شريط التبويب الآن — لا محاكاة `pushState` مباشرة (كانت محدودةً في و-١٣
  لغياب شريط تبويب حقيقيّ وقتها؛ التفصيل الكامل والسبب في `و-١٥.md` §١.٣
  و`nav.test.ts` الذي أثبت الآلية حتميًّا على مستوى الوحدة). وتُقاس مرّةً
  واحدة عند مقاس الأساس: سلوك السجلّ لا يتغيّر بعرض الشاشة.
*/
async function measureHistory(browser) {
  const ctx = await browser.newContext({ viewport: { width: 375, height: 812 }, locale: 'ar' })
  const page = await ctx.newPage()

  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.fill('#student_no', STUDENT)
  await page.fill('#pin', PIN)
  await page.click('button[type=submit]')
  await page.waitForFunction(() => !document.querySelector('#student_no'), { timeout: 8000 })

  const rootUrl = new URL(page.url()).pathname
  if (rootUrl !== '/') {
    failures.push(`ق-٢٢٠: الجذر بعد الدخول ${rootUrl} لا '/' — الروابط العميقة لن تنجو`)
  }

  // ق-٢٢١ — إعادة نقر التبويب النشط («الرئيسية»، وهو النشط بعد الدخول) لا
  // تُنشئ مدخلًا.
  const beforeRetap = await page.evaluate(() => history.length)
  await page.click('[data-key="deck"]')
  const afterRetap = await page.evaluate(() => history.length)
  if (afterRetap - beforeRetap > 0) {
    failures.push(`ق-٢٢١: نقرٌ ثانٍ على التبويب النشط أضاف مدخلًا (${beforeRetap} ⇐ ${afterRetap})`)
  }

  // ق-٢٢٠ — ثلاث شاشات عميقة (الوقود ← التشكيل ← الصدارة) ثمّ ثلاث رجعات،
  // كلّ رجعة يجب أن تعيد المسار الصحيح بالضبط.
  const path = async () => new URL(page.url()).pathname
  await page.click('[data-key="station"]')
  await page.click('[data-key="formation"]')
  await page.click('[data-key="board"]')
  if ((await path()) !== '/board') {
    failures.push(`ق-٢٢٠: بعد ثلاث نقرات المسار ${await path()} لا '/board'`)
  }

  const expectedBack = ['/formation', '/station', '/']
  for (const expected of expectedBack) {
    await Promise.all([page.waitForURL(`**${expected === '/' ? '/' : expected}`, { timeout: 4000 }), page.goBack()])
    const got = await path()
    if (got !== expected) {
      failures.push(`ق-٢٢٠: رجوعٌ أعطى ${got} والمتوقَّع ${expected} — زرّ أندرويد سيهبط في مكانٍ خطأ`)
    }
  }

  await ctx.close()
}

const browser = await chromium.launch()

console.log('═══ قياس حيّ — ثلاثة مقاسات ═══')
for (const viewport of VIEWPORTS) {
  await measureAt(browser, viewport)
}
await measureHistory(browser)
await browser.close()

if (failures.length) {
  console.error(`\n❌ ${failures.length} مخالفة:`)
  for (const f of failures) console.error(`   ${f}`)
  process.exit(1)
}
console.log('\n✅ ق-٢١٧ · ق-٢٢٠ · ق-٢٢١ · ق-٢٢٢ · ق-٢٢٣ — مقيسة ومجتازة عند ٣٢٠ و٣٧٥ و١٢٨٠ و١٤٤٠px.')
