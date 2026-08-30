import { chromium } from 'playwright'
const S = process.argv[2]
const browser = await chromium.launch()

for (const [who, pin, label] of [['1001','1234','normal'], ['1002','1234','empty'],
                                  ['1003','1234','max'], ['1004','1234','grounded']]) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 },
                                         deviceScaleFactor: 2, locale: 'ar' })
  const page = await ctx.newPage()
  const errors = []
  page.on('console', m => m.type() === 'error' && errors.push(m.text()))
  page.on('pageerror', e => errors.push(String(e)))

  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' })
  await page.fill('#student_no', who)
  await page.fill('#pin', pin)
  await page.click('button[type=submit]')
  await page.waitForSelector('text=بطاقة الطيار', { timeout: 8000 })
  await page.waitForTimeout(700)
  await page.screenshot({ path: `${S}/deck-${label}.png`, fullPage: true })
  const text = await page.locator('body').innerText()
  console.log(`── ${label} (${who}) ──`)
  console.log(text.split('\n').filter(Boolean).map(l => '   '+l).join('\n'))
  if (errors.length) console.log('   ⚠️ أخطاء وحدة التحكّم:', errors.join(' | '))
  await ctx.close()
}

// شاشة الدخول وحالة الخطأ
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()
await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' })
await page.screenshot({ path: `${S}/login.png`, fullPage: true })
await page.fill('#student_no', '9999'); await page.fill('#pin', '0000')
await page.click('button[type=submit]')
await page.waitForSelector('[role=alert]')
console.log('── فشل الدخول ──\n   ' + await page.locator('[role=alert]').innerText())
await page.screenshot({ path: `${S}/login-error.png`, fullPage: true })
await browser.close()
