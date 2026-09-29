/**
 * @covers ق-٢٥٦
 *
 * محطة التزوّد — **الفرق بين لترٍ متوقَّع ولترٍ محتسَب.**
 *
 * الطالب يرى مهمّة سربه قبل اعتماد المشرف، ورقمُ اللترات حاضرٌ في الحالتين.
 * فإن لم يُميَّز نصًّا، قرأ السرب رقمًا **متوقَّعًا** على أنه رصيدٌ له —
 * ثم تغيّر بعد الاعتماد بلا تفسير. ولا يكشف ذلك قياسٌ بصريّ: التخطيط نفسه
 * في الحالتين.
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { asDecimal } from '../api/brand'
import type { Station } from '../api/types/me'

// `asDecimal` لا `as Station`: الوسم موجودٌ لسببٍ، وتجاوزُه في الاختبار
// يجعل الاختبار يقبل ما يرفضه الإنتاج (ADR-009).
const station = (state: 'draft' | 'approved' | null): Station => ({
  team: { name: 'سرب الفرقان', litres: asDecimal('149.26') },
  tank_capacity_l: asDecimal('500.00'),
  recent: [],
  week_task:
    state === null
      ? null
      : {
          name: 'العشاء',
          state,
          assessed: true,
          total_pct: asDecimal('80.00'),
          litres: asDecimal('96.00'),
        },
})

const stationFn = vi.fn()

vi.mock('../api', () => ({
  api: { me: { station: () => stationFn() } },
  ApiError: class extends Error {},
}))

afterEach(cleanup)

async function show(state: 'draft' | 'approved' | null) {
  stationFn.mockResolvedValue(station(state))
  const { default: Screen } = await import('../screens/Station')
  render(<Screen />)
  await waitFor(() => expect(screen.getByText('سرب الفرقان')).toBeInTheDocument())
}

describe('محطة التزوّد — مهمّة هذا الأسبوع', () => {
  it('مسوّدة: يقول النصّ إنّ اللترات **متوقَّعة ولم تُحتسب**', async () => {
    await show('draft')
    expect(screen.getByText(/مهمّة هذا الأسبوع: العشاء/)).toBeInTheDocument()
    expect(screen.getByText(/مسوّدة — بانتظار اعتماد المشرف/)).toBeInTheDocument()
    expect(screen.getByText(/لم تُحتسب بعد/)).toBeInTheDocument()
  })

  it('معتمَد: يختفي وصفُ التوقّع ويُعلَن الاعتماد', async () => {
    await show('approved')
    expect(screen.getByText('معتمَد')).toBeInTheDocument()
    expect(screen.queryByText(/لم تُحتسب بعد/)).not.toBeInTheDocument()
    expect(screen.getByText('لترات هذه المهمّة')).toBeInTheDocument()
  })

  it('بلا مهمّة: لا لوح أصلًا — حالةٌ مصمَّمة لا فراغ', async () => {
    await show(null)
    expect(screen.queryByText(/مهمّة هذا الأسبوع/)).not.toBeInTheDocument()
    expect(screen.getByText('وقود السرب')).toBeInTheDocument()
  })
})
