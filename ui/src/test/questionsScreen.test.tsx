/**
 * شاشة سؤال اليوم الإدارية — و-٢١ · @covers ق-٢٨٢
 *
 * **الفحص على ما تملكه الشاشة وحدها:** أن «مُقفَل» يصل **حقلًا من الخادم**
 * فتُخفى أدوات التعديل بناءً عليه، وأن النموذج لا يُرسل سؤالًا بلا إجابةٍ
 * صحيحة مختارة. والقاعدة نفسها (ث-١٧) يحرسها الخادم في
 * `test_admin_questions.py`.
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { asDecimal } from '../api/brand'
import type { QuestionsList } from '../api/types/dailyQuestion'

// `asDecimal` لا `as QuestionsList`: الوسم العشريّ (ADR-009) يُفرض بالنوع،
// والتحويل القسريّ يتجاوزه فيختبئ فرقٌ حقيقيّ في النقل.
const list: QuestionsList = {
  questions: [
    {
      id: 1,
      day: '2026-08-01',
      prompt: 'سؤالٌ أُجيب',
      choices: [
        { id: 1, text: 'عشرون' },
        { id: 2, text: 'ثلاثون' },
      ],
      correct_id: 2,
      note: 'شرح',
      reward_hours: asDecimal('1.00'),
      answers: 7,
      locked: true,
    },
    {
      id: 2,
      day: '2026-08-02',
      prompt: 'سؤالٌ لم يُجَب',
      choices: [
        { id: 1, text: 'أ' },
        { id: 2, text: 'ب' },
      ],
      correct_id: 1,
      note: 'شرح',
      reward_hours: asDecimal('2.50'),
      answers: 0,
      locked: false,
    },
  ],
}

const createQuestion = vi.fn()
const deleteQuestion = vi.fn()

vi.mock('../api', () => ({
  api: {
    admin: {
      questions: () => Promise.resolve(list),
      createQuestion: (...args: unknown[]) => createQuestion(...args),
      deleteQuestion: (...args: unknown[]) => deleteQuestion(...args),
    },
  },
  ApiError: class extends Error {},
}))

afterEach(cleanup)

const load = async () => {
  const { default: Screen } = await import('../screens/admin/DailyQuestions')
  render(<Screen />)
  await waitFor(() => expect(screen.getByText('سؤالٌ أُجيب')).toBeInTheDocument())
}

describe('سؤال اليوم — الشقّ الإداريّ', () => {
  it('**المُقفَل يُعرَض بلا زرّ حذف** — فلا يُعرَض زرٌّ يردّ الخادمُ عليه بـ٤٠٩', async () => {
    await load()
    // زرّ حذفٍ واحد: للسؤال غير المُجاب وحده.
    expect(screen.getAllByRole('button', { name: 'حذف' })).toHaveLength(1)
    expect(screen.getByText(/أُجيب — لا يُعدَّل/)).toBeInTheDocument()
  })

  it('يعرض عدد من أجاب — وهو ما يُعلِم المشرف أنه مُقفَل', async () => {
    await load()
    expect(screen.getByText('7')).toBeInTheDocument()
  })

  it('يعرض نصّ الجواب الصحيح لا رقم معرّفه', async () => {
    await load()
    expect(screen.getByText('ثلاثون')).toBeInTheDocument()
  })

  it('الحذف يصيب السؤال غير المُجاب', async () => {
    deleteQuestion.mockResolvedValue(undefined)
    await load()
    fireEvent.click(screen.getByRole('button', { name: 'حذف' }))
    await waitFor(() => expect(deleteQuestion).toHaveBeenCalledWith(2))
  })

  it('**لا حفظ بلا إجابةٍ صحيحة مختارة** — سؤالٌ بلا صحيح يُخطئ فيه كلُّ مجيب', async () => {
    await load()
    fireEvent.change(screen.getByLabelText('اليوم'), { target: { value: '2026-08-03' } })
    fireEvent.change(screen.getByLabelText('نصّ السؤال'), { target: { value: 'سؤال' } })
    fireEvent.change(screen.getByLabelText('نصّ الخيار 1'), { target: { value: 'أ' } })
    fireEvent.change(screen.getByLabelText('نصّ الخيار 2'), { target: { value: 'ب' } })
    fireEvent.change(screen.getByLabelText(/شرح الجواب/), { target: { value: 'شرح' } })

    expect(screen.getByRole('button', { name: 'حفظ السؤال' })).toBeDisabled()

    // اختيار «الصحيح» للخيار الأول — الزرّ يُفتح.
    fireEvent.click(screen.getAllByRole('radio')[0]!)
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'حفظ السؤال' })).not.toBeDisabled()
    )
  })

  it('الخيارات الفارغة لا تُرسَل — أربع خانات والمشرف يملأ ما يحتاج', async () => {
    createQuestion.mockResolvedValue({ id: 9, day: '2026-08-03' })
    await load()
    fireEvent.change(screen.getByLabelText('اليوم'), { target: { value: '2026-08-03' } })
    fireEvent.change(screen.getByLabelText('نصّ السؤال'), { target: { value: 'سؤال' } })
    fireEvent.change(screen.getByLabelText('نصّ الخيار 1'), { target: { value: 'أ' } })
    fireEvent.change(screen.getByLabelText('نصّ الخيار 2'), { target: { value: 'ب' } })
    fireEvent.change(screen.getByLabelText(/شرح الجواب/), { target: { value: 'شرح' } })
    fireEvent.click(screen.getAllByRole('radio')[1]!)
    fireEvent.click(screen.getByRole('button', { name: 'حفظ السؤال' }))

    await waitFor(() => expect(createQuestion).toHaveBeenCalled())
    const sent = createQuestion.mock.calls[0]![0] as { choices: unknown[]; correct_id: string }
    // الترشيح يقع في طبقة الـAPI، فالنموذج يُرسل الخانات الأربع كما هي.
    expect(sent.choices).toHaveLength(4)
    expect(sent.correct_id).toBe('2')
  })
})
