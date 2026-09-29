/**
 * @covers ق-٢٥٤
 *
 * شاشة أسبوع الوقود — **أوّل اختبار شاشة في المستودع**.
 *
 * كانت الشاشات تُقاس بصريًّا وحدها (`visual-qa`)، وذاك يثبت التخطيط والتباين
 * وأرضية اللمس — **ولا يثبت السلوك**.
 *
 * والسلوك المحروس هنا: درجات أسبوعٍ لا تظهر على أسبوعٍ آخر. وهو يعمل اليوم
 * بآلية غير مقصودة — `useAsync` يمرّ بحالة تحميل عند تبديل الأسبوع فيُفكَّك
 * المكوّن وتُصفَّر حالته المحليّة. فالاختبار يحرس **النتيجة** لا الآلية:
 * إن أُلغي وميضُ التحميل يومًا (إبقاء البيانات القديمة أثناء الجلب) لسقط
 * هذا الاختبار بدل أن يُكتشف الأمر بعين مشرفٍ حفظ ما رآه.
 *
 * (ظُنّ أوّلًا أنه عطلٌ قائم، وأُثبت العكس بالزرع: إعادةُ المفتاح القديم لم
 * تُسقط الاختبار.)
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { asDecimal } from '../api/brand'
import type { FuelWeek } from '../api/types/fuel'

// `asDecimal` لا `as FuelWeek` — انظر التعليق في `stationWeekTask`.
const week = (weekStart: string, scorePct: string | null): FuelWeek => ({
    week_start: weekStart,
    state: scorePct ? 'draft' : 'unopened',
    approved_at: null,
    teams: [{ id: 1, name: 'سرب الفرقان' }],
    tasks: [
      {
        activity_id: 7,
        name: 'العشاء',
        litres_full: asDecimal('120.00'),
        team_id: 1,
        team_name: 'سرب الفرقان',
        assessed: Boolean(scorePct),
        total_pct: asDecimal(scorePct ?? '0.00'),
        litres: asDecimal('0.00'),
        criteria: [
          {
            id: 11,
            name: 'الطعم',
            weight_pct: asDecimal('100.00'),
            score_pct: scorePct === null ? null : asDecimal(scorePct),
          },
        ],
      },
    ],
})

const fuelWeek = vi.fn()

vi.mock('../api', () => ({
  api: {
    admin: {
      fuelWeek: (...args: unknown[]) => fuelWeek(...args),
      fuelActivities: () => Promise.resolve({ activities: [] }),
      createFuelActivity: () => Promise.resolve({ id: 1 }),
      assignFuelTeam: () => Promise.resolve(week('2026-09-27', null)),
      saveFuelScores: () => Promise.resolve(week('2026-09-27', '80.00')),
      removeFuelTask: () => Promise.resolve(week('2026-09-27', null)),
      approveFuelWeek: () => Promise.resolve(week('2026-09-27', '80.00')),
    },
  },
  ApiError: class extends Error {},
}))

afterEach(cleanup)
beforeEach(() => fuelWeek.mockReset())

const scoreBox = () => screen.getByLabelText('درجة الطعم') as HTMLInputElement

describe('أسبوع الوقود — السلوك لا التخطيط', () => {
  it('يعرض درجات الأسبوع المحمَّل', async () => {
    fuelWeek.mockResolvedValue(week('2026-09-20', '55.00'))
    const { default: Screen } = await import('../screens/admin/FuelActivities')
    render(<Screen />)
    await waitFor(() => expect(scoreBox()).toBeInTheDocument())
    expect(scoreBox().value).toBe('55.00')
  })

  it('**الانتقال إلى أسبوعٍ غير مقيَّم يُفرِغ الدرجات** — لا يُبقي درجات سابقه', async () => {
    fuelWeek.mockImplementation((weekStart?: string) =>
      Promise.resolve(
        weekStart === '2026-09-27' ? week('2026-09-27', null) : week('2026-09-20', '55.00')
      )
    )
    const { default: Screen } = await import('../screens/admin/FuelActivities')
    render(<Screen />)
    await waitFor(() => expect(scoreBox()).toBeInTheDocument())
    expect(scoreBox().value).toBe('55.00')

    // المشرف ينتقل إلى أسبوعٍ آخر لم يُقيَّم. `fireEvent.change` لا
    // `userEvent.type`: حقل التاريخ يبتلع الكتابة حرفًا حرفًا في jsdom.
    fireEvent.change(screen.getByLabelText(/أسبوع التقييم/), {
      target: { value: '2026-09-27' },
    })

    await waitFor(() => expect(fuelWeek).toHaveBeenCalledWith('2026-09-27'))
    await waitFor(() => expect(scoreBox().value).toBe(''))
  })
})
