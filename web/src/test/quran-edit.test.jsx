import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '../App'

/*
  و-٦ — سلوك ملحوظ لا تفاصيل تنفيذ، بنفس منهج `admin-rules.test.jsx`.
*/

const ADMIN = { user: { id: 1, full_name: 'بندر الشمري', student_no: '1001', role: 'admin' } }
const DECK = {
  rank: { name: 'طيار أول', tier: 2 },
  hours: '611.25',
  next_rank: { name: 'رائد سرب', at_hours: '900.00', progress_pct: 42.3, remaining: '288.75' },
  flight: { grounded: false, last_activity_on: '2026-08-28' },
  team: { name: 'سرب الفرقان', rank_in_org: null },
}
const STUDENTS = { students: [{ id: 7, full_name: 'أحمد سالم' }] }
const EVENTS = {
  events: [{ id: 5, kind: 'quran', delta: '10.00', occurred_on: '2026-08-20', reason: null }],
}

function mockApi({ role = 'admin', reverseOk = true, entryOk = true } = {}) {
  globalThis.fetch = vi.fn(async (url) => {
    const ok = (json, status = 200) => ({ ok: true, status, json: async () => json })
    const fail = (status, message) => ({ ok: false, status, json: async () => ({ message }) })
    if (url.includes('/auth/me')) return ok({ user: { ...ADMIN.user, role } })
    if (url.includes('/me/deck')) return ok(DECK)
    if (url.includes('/me/events')) return ok({ events: [] })
    if (url.includes('/admin/quran/students')) return ok(STUDENTS)
    if (url.includes('/admin/quran/events')) return ok(EVENTS)
    if (url.includes('/admin/quran/entry')) {
      return entryOk ? ok({ id: 99, delta: '15.00', kind: 'manual' }, 201) : fail(422, 'لا وزن للنشاط.')
    }
    if (url.includes('/reverse')) {
      return reverseOk ? ok({ id: 100, delta: '-10.00', kind: 'correction' }, 201) : fail(422, 'التصحيح يوجب سببًا مكتوبًا.')
    }
    return { ok: false, status: 404, json: async () => ({ message: 'غير متوقَّع' }) }
  })
}

beforeEach(() => vi.restoreAllMocks())

describe('التصحيح والتعديل القرآني — و-٦', () => {
  it('اختيار طالب يعرض أحداثه كما وصلت من الخادم', async () => {
    mockApi()
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'التصحيح والتعديل القرآني' }))
    await userEvent.selectOptions(
      await screen.findByLabelText('الطالب', { selector: '#qe_student' }),
      '7',
    )
    expect(await screen.findByText('quran')).toBeInTheDocument()
    expect(screen.getByText('10.00')).toBeInTheDocument()
  })

  it('التصحيح: يرسل السبب ويعرض النتيجة كما وصلت — لا حساب هنا', async () => {
    mockApi()
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'التصحيح والتعديل القرآني' }))
    await userEvent.selectOptions(
      await screen.findByLabelText('الطالب', { selector: '#qe_student' }),
      '7',
    )
    await userEvent.click(await screen.findByRole('button', { name: 'تصحيح' }))
    await userEvent.type(screen.getByLabelText('سبب التصحيح — إلزاميّ'), 'خطأ في التصدير')
    await userEvent.click(screen.getByRole('button', { name: 'تأكيد التصحيح' }))

    const call = globalThis.fetch.mock.calls.find(([url]) => url.includes('/reverse'))
    expect(call).toBeTruthy()
    expect(JSON.parse(call[1].body)).toEqual({ reason: 'خطأ في التصدير' })
  })

  it('التصحيح بلا سبب: زرّ التأكيد معطَّل — لا طلب يُرسَل', async () => {
    mockApi()
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'التصحيح والتعديل القرآني' }))
    await userEvent.selectOptions(
      await screen.findByLabelText('الطالب', { selector: '#qe_student' }),
      '7',
    )
    await userEvent.click(await screen.findByRole('button', { name: 'تصحيح' }))
    expect(screen.getByRole('button', { name: 'تأكيد التصحيح' })).toBeDisabled()
  })

  it('الإضافة اليدوية: الساعات المعروضة نصٌّ من الخادم بلا حساب', async () => {
    mockApi()
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'التصحيح والتعديل القرآني' }))

    await userEvent.selectOptions(screen.getByLabelText('الطالب', { selector: '#qe_add_student' }), '7')
    await userEvent.type(screen.getByLabelText('نوع النشاط'), 'memorize')
    await userEvent.type(screen.getByLabelText('الكمّية'), '3')
    await userEvent.type(screen.getByLabelText('تاريخ الوقوع'), '2026-08-20')
    await userEvent.type(screen.getByLabelText('السبب — إلزاميّ'), 'غاب عن تصدير راصد')
    await userEvent.click(screen.getByRole('button', { name: 'إضافة' }))

    expect(await screen.findByText('15.00')).toBeInTheDocument()
  })

  it('الإضافة: خطأ الخادم (٤٢٢) يُعرض نصًّا كما وصل', async () => {
    mockApi({ entryOk: false })
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'التصحيح والتعديل القرآني' }))

    await userEvent.selectOptions(screen.getByLabelText('الطالب', { selector: '#qe_add_student' }), '7')
    await userEvent.type(screen.getByLabelText('نوع النشاط'), 'نشاط-غريب')
    await userEvent.type(screen.getByLabelText('الكمّية'), '3')
    await userEvent.type(screen.getByLabelText('تاريخ الوقوع'), '2026-08-20')
    await userEvent.type(screen.getByLabelText('السبب — إلزاميّ'), 'سبب')
    await userEvent.click(screen.getByRole('button', { name: 'إضافة' }))

    expect(await screen.findByText('لا وزن للنشاط.')).toBeInTheDocument()
  })

  it('زرّ الشاشة لا يظهر لطيار', async () => {
    mockApi({ role: 'pilot' })
    render(<App />)
    await screen.findByText('بندر الشمري')
    expect(screen.queryByRole('button', { name: 'التصحيح والتعديل القرآني' })).not.toBeInTheDocument()
  })
})
