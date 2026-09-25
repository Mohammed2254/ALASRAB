/**
 * @covers ق-٢٢٠, ق-٢٢١
 *
 * إثباتٌ حتميّ لآلية السجلّ في `nav/history.ts` — لا محاكاةٌ عبر `page.goto`.
 *
 * **لماذا اختبار وحدة لا `page.goBack()` في `visual-qa.mjs`؟** لأن الشاشات
 * الحقيقية ما زالت واحدة (`Login`) — البطاقة وبقيّة الـ٢٥ مسارًا لا تُرسَم بعد
 * (و-١٥..و-١٨)، ولا شريط تبويب يُنقَر عليه حتى و-١٥. فمحاكاةُ «ثلاث شاشات
 * عميقة» بنقراتٍ حقيقية اليوم إمّا وهميّة (لا شيء يُنقَر) أو تقفز فوق `go()`
 * مباشرةً (`page.evaluate(() => history.pushState(...))`) — وتلك ليست اختبارًا
 * للكود بل لتوقيعه. الدالّة الحقيقية `go()` تُختبَر هنا **بذاتها**، حتميًّا،
 * بلا حاجة لشاشةٍ لم تُبنَ بعد. القياس الحيّ في `visual-qa.mjs::measureHistory`
 * يبقى مكمِّلًا لا بديلًا: يثبت أنّ **متصفّحًا حقيقيًّا** لا يخالف `init()`
 * (`replaceState` لا `pushState` عند الدخول) — الفرضية الوحيدة التي لا يغطّيها
 * jsdom بثقة كاملة.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest'

async function freshHistory() {
  vi.resetModules()
  window.history.replaceState(null, '', '/')
  return import('../nav/history')
}

/** ينتظر `popstate` فعليًّا لا يخمّن توقيته — jsdom يُصدره كمهمّة لا حدثًا فوريًّا. */
function nextPopstate(): Promise<void> {
  return new Promise((resolve) => {
    window.addEventListener('popstate', () => resolve(), { once: true })
  })
}

beforeEach(() => {
  window.history.replaceState(null, '', '/')
})

describe('nav/history — ق-٢٢٠ (ثلاث شاشات عميقة ثم الجذر)', () => {
  it('التهيئة تستبدل المدخل الابتدائي ولا تضيف عليه', async () => {
    const before = window.history.length
    const { init } = await freshHistory()
    init()
    // `replaceState` لا `pushState`: طولُ السجلّ لا يتغيّر — وإلّا احتاج
    // الطالب ضغطتَي رجوع ليغادر أوّل شاشة (نفس الفخّ الموثَّق في تعليق الملفّ).
    expect(window.history.length).toBe(before)
  })

  it('ثلاث انتقالات ثم ثلاث رجعات تعيد الترتيب المعاكس بالضبط', async () => {
    const { init, listen, go, getScreen } = await freshHistory()
    init()
    const stop = listen()

    go('readings')
    go('station')
    go('formation')
    expect(getScreen()).toBe('formation')

    await Promise.all([nextPopstate(), window.history.back()])
    expect(getScreen()).toBe('station')

    await Promise.all([nextPopstate(), window.history.back()])
    expect(getScreen()).toBe('readings')

    await Promise.all([nextPopstate(), window.history.back()])
    expect(getScreen()).toBe('deck')

    stop()
  })

  it('مسارٌ مجهول عند التهيئة يهبط على الجذر لا شاشة خطأ', async () => {
    window.history.replaceState(null, '', '/رابط-قديم-مكسور')
    const { init, getScreen } = await freshHistory()
    init()
    expect(getScreen()).toBe('deck')
  })
})

describe('nav/history — ق-٢٢١ (إعادة نقر الشاشة النشطة لا تُنشئ مدخلًا)', () => {
  it('go() إلى الشاشة الحالية نفسها لا تضيف مدخلًا ولا تُخطر المستمعين', async () => {
    const { init, subscribe, go, getScreen } = await freshHistory()
    init()
    go('readings')
    const afterFirst = window.history.length

    const notified = vi.fn()
    const stop = subscribe(notified)

    go('readings') // نقرٌ ثانٍ على التبويب النشط نفسه
    expect(window.history.length).toBe(afterFirst)
    expect(getScreen()).toBe('readings')
    expect(notified).not.toHaveBeenCalled()

    stop()
  })

  it('go() إلى شاشة مختلفة تضيف مدخلًا واحدًا وتُخطر المستمعين', async () => {
    const { init, subscribe, go } = await freshHistory()
    init()
    const before = window.history.length

    const notified = vi.fn()
    const stop = subscribe(notified)
    go('station')

    expect(window.history.length).toBe(before + 1)
    expect(notified).toHaveBeenCalledTimes(1)

    stop()
  })
})

describe('nav/history — replace() و listen()', () => {
  it('replace() تستبدل الشاشة الحالية بلا مدخل جديد', async () => {
    const { init, go, replace, getScreen } = await freshHistory()
    init()
    go('station')
    const before = window.history.length

    replace('deck')
    expect(getScreen()).toBe('deck')
    expect(window.history.length).toBe(before)
  })

  it('popstate خارجيّ (زرّ رجوع فعليّ) يُحدِّث getScreen ويُخطر المشتركين', async () => {
    const { init, listen, go, subscribe, getScreen } = await freshHistory()
    init()
    const stop = listen()
    go('station')

    const notified = vi.fn()
    const stopSub = subscribe(notified)

    await Promise.all([nextPopstate(), window.history.back()])

    expect(getScreen()).toBe('deck')
    expect(notified).toHaveBeenCalledTimes(1)

    stopSub()
    stop()
  })
})
