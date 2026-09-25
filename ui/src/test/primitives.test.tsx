/**
 * @covers ق-٢٢٩, ق-٢٣٠
 */
import { cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import FormationSky from '../ui/FormationSky'
import Podium, { type BoardEntry } from '../ui/Podium'
import ProgressBar from '../ui/ProgressBar'
import SegmentedControl from '../ui/SegmentedControl'
import StatCard from '../ui/StatCard'

afterEach(cleanup)

describe('SegmentedControl — ق-٢٢٩ (المؤشّر من أوّل رسم لا من الصفر)', () => {
  it('يقيس إزاحة الزرّ النشط بعينه من الرسم الأوّل، لا يفترض الأوّل أو الصفر', () => {
    // jsdom لا يحسب تخطيطًا حقيقيًّا — نُحاكي offsetLeft/offsetWidth بمفتاح
    // كل زرّ (`data-key`) كي يقيس التنفيذ الفعليّ لا قيمة افتراضية صامتة.
    const LAYOUT: Record<string, { left: number; width: number }> = {
      a: { left: 0, width: 50 },
      b: { left: 54, width: 60 },
    }
    Object.defineProperty(HTMLElement.prototype, 'offsetLeft', {
      configurable: true,
      get(this: HTMLElement) {
        return LAYOUT[this.dataset.key ?? '']?.left ?? -1
      },
    })
    Object.defineProperty(HTMLElement.prototype, 'offsetWidth', {
      configurable: true,
      get(this: HTMLElement) {
        return LAYOUT[this.dataset.key ?? '']?.width ?? -1
      },
    })

    const { container } = render(
      <SegmentedControl
        options={[
          { key: 'a', label: 'أ' },
          { key: 'b', label: 'ب' },
        ]}
        value="b"
        onChange={() => {}}
      />
    )

    const thumb = container.querySelector('span[aria-hidden="true"]') as HTMLElement
    expect(thumb).toBeTruthy()
    // القيمة النشطة "b" — فالمؤشّر يجب أن يُقاس على زرّها بعينه (٥٤/٦٠)
    // لا على الزرّ الأوّل (٠/٥٠) ولا على قيمةٍ افتراضية صامتة.
    expect(thumb.style.transform).toBe('translateX(54px)')
    expect(thumb.style.width).toBe('60px')
  })
})

describe('prefers-reduced-motion — ق-٢٣٠ (حالة نهائية ثابتة فورًا)', () => {
  it('StatCard: العدّاد يظهر بقيمته النهائية بلا تصاعد', () => {
    vi.spyOn(window, 'matchMedia').mockImplementation(
      (query) => ({ matches: query.includes('reduce'), media: query }) as MediaQueryList
    )
    const { container } = render(<StatCard value={428} label="ساعة هذا الأسبوع" />)
    expect(container.querySelector('.num')?.textContent).toBe('428')
    vi.restoreAllMocks()
  })

  it('Podium: عناصر المنصّة والحوامل تُرسَم بحالتها النهائية (لا عتمة ولا ارتفاع صفريّ عالق)', () => {
    vi.spyOn(window, 'matchMedia').mockImplementation(
      (query) => ({ matches: query.includes('reduce'), media: query }) as MediaQueryList
    )
    const top3: [BoardEntry, BoardEntry, BoardEntry] = [
      { name: 'ماجد', value: 1563, chg: 0 },
      { name: 'بندر', value: 614.25, chg: 1 },
      { name: 'سالم', value: 18.5, chg: -1 },
    ]
    const { container } = render(<Podium top3={top3} rest={[]} />)
    const items = container.querySelectorAll<HTMLElement>('[data-podium-item]')
    const stands = container.querySelectorAll<HTMLElement>('[data-stand]')
    expect(items.length).toBe(3)
    for (const el of items) expect(el.style.opacity).toBe('1')
    // GSAP يُسقط الحدود المحايدة (`scaleY(1)`) من نصّ `transform` لأنها
    // لا تُغيّر شيئًا مرئيًّا — فالتأكيد هنا على **غياب** الحالة العالقة
    // (`scale-y-0` من Tailwind) لا على حرفية النصّ. والنمط المضمَّن يتغلّب
    // على صنف Tailwind بصريًّا بصرف النظر عمّا يكتبه GSAP حرفيًّا.
    for (const el of stands) expect(el.style.transform).not.toContain('scaleY(0)')
    vi.restoreAllMocks()
  })

  it('FormationSky: شرائح الطائرات المحلِّقة تُرسَم ظاهرة فورًا (لا عالقة عند دوران/عتمة البداية)', () => {
    vi.spyOn(window, 'matchMedia').mockImplementation(
      (query) => ({ matches: query.includes('reduce'), media: query }) as MediaQueryList
    )
    const { container } = render(
      <FormationSky
        flying={[
          { name: 'خالد', pct: 100 },
          { name: 'عبدالله', pct: 32 },
        ]}
        landed={[]}
      />
    )
    const slots = container.querySelectorAll<HTMLElement>('[data-slot]')
    expect(slots.length).toBe(2)
    // نفس ملاحظة اختبار Podium أعلاه: `rotate(0deg)`/`scale(0.4)` محايدة أو
    // ابتدائية — التأكيد على غياب حالة الدخول العالقة (دوران/تصغير) لا على
    // حرفية سلسلة `transform`.
    for (const el of slots) {
      expect(el.style.opacity).toBe('1')
      expect(el.style.transform).not.toContain('scale(0.4')
    }
    vi.restoreAllMocks()
  })
})

describe('prefers-reduced-motion — لا يمنع الانتقالات المدفوعة بـCSS المحضة', () => {
  it('ProgressBar يبقى يعتمد على useEnter (CSS) — القاعدة الشاملة في base.css تكفيه بلا مو.ts', () => {
    // لا حاجة لمحاكاة matchMedia هنا: ProgressBar لا يستورد motion/mo إطلاقًا
    // (تصميم و-١٤.md §٢ قرار ٥)، فلا يوجد GSAP يتجاوز قاعدة `transition-duration`.
    const { container } = render(<ProgressBar pct={42} />)
    expect(container.querySelector('[role="progressbar"]')).toBeTruthy()
  })
})
