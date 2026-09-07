import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '../App'

/*
  تحضير القراءة — و-١١. سلوك ملحوظ لا تفاصيل تنفيذ، نفس منهج
  `quran-edit.test.jsx`.
*/

const ADMIN = { user: { id: 1, full_name: 'بندر الشمري', student_no: '1001', role: 'admin' } }
const DECK = {
  rank: { name: 'طيار أول', tier: 2 },
  hours: '611.25',
  next_rank: { name: 'رائد سرب', at_hours: '900.00', progress_pct: 42.3, remaining: '288.75' },
  flight: { grounded: false, last_activity_on: '2026-08-28' },
  team: { name: 'سرب الفرقان', rank_in_org: null },
}
const WEEK = {
  week_start: '2026-09-06',
  days: [
    { date: '2026-09-06', weekday: 'الأحد', completed: true, pages: 10 },
    { date: '2026-09-07', weekday: 'الاثنين', completed: false, pages: 0 },
    { date: '2026-09-08', weekday: 'الثلاثاء', completed: false, pages: 0 },
    { date: '2026-09-09', weekday: 'الأربعاء', completed: false, pages: 0 },
  ],
  pages_total: 10,
  target_pages: 28,
  percent: 35.7,
  struggling: true,
}
const TAHDIR_MINE = { submissions: [], week: WEEK }
const STUDENTS = { students: [{ id: 7, full_name: 'أحمد سالم' }] }
const QUEUE = {
  submissions: [
    { id: 5, student_name: 'أحمد سالم', read_on: '2026-09-06', pages: 10, book_title: 'كتاب' },
  ],
}
const REPORT = {
  week_start: '2026-09-06',
  students: [
    { user_id: 1, full_name: 'بندر الشمري', days_completed: 1, pages_total: 10, percent: 35.7, struggling: true },
    { user_id: 7, full_name: 'أحمد سالم', days_completed: 0, pages_total: 0, percent: 0, struggling: true },
  ],
}

function mockApi({ role = 'admin', submitOk = true, entryOk = true } = {}) {
  globalThis.fetch = vi.fn(async (url, init) => {
    const ok = (json, status = 200) => ({ ok: true, status, json: async () => json })
    const fail = (status, message) => ({ ok: false, status, json: async () => ({ message }) })
    if (url.includes('/auth/me')) return ok({ user: { ...ADMIN.user, role } })
    if (url.includes('/me/deck')) return ok(DECK)
    if (url.includes('/me/events')) return ok({ events: [] })
    if (url.includes('/admin/quran/students')) return ok(STUDENTS)
    if (url.includes('/admin/tahdir/report')) return ok(REPORT)
    if (url.includes('/admin/tahdir/entry')) {
      return entryOk ? ok({ id: 9, status: 'approved', hours: '10.00' }, 201) : fail(422, 'تحضير القراءة يكون من الأحد إلى الأربعاء فقط.')
    }
    if (url.includes('/admin/tahdir')) return ok(QUEUE)
    if (url.includes('/admin/readings/approve')) return ok({ results: [{ submission_id: 5, status: 'approved', hours: '1.50' }] })
    if (url.includes('/me/tahdir')) {
      if (init?.method === 'POST') {
        return submitOk ? ok({ id: 12, status: 'pending' }, 201) : fail(422, 'تحضير القراءة يكون من الأحد إلى الأربعاء فقط.')
      }
      return ok(TAHDIR_MINE)
    }
    return { ok: false, status: 404, json: async () => ({ message: 'غير متوقَّع' }) }
  })
}

beforeEach(() => vi.restoreAllMocks())

describe('تحضير القراءة — و-١١', () => {
  it('الطالب: التقرير الأسبوعي يُعرض كما وصل من الخادم — لا حساب هنا', async () => {
    mockApi({ role: 'pilot' })
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'تحضير القراءة' }))
    expect(await screen.findByText('35.7%')).toBeInTheDocument()
    expect(screen.getByText('متعثّر')).toBeInTheDocument()
    expect(screen.getByText('مكتمل ✓')).toBeInTheDocument()
  })

  it('الطالب: إرسال ناجح يعيد تحميل التقرير', async () => {
    mockApi({ role: 'pilot' })
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'تحضير القراءة' }))
    await screen.findByText('35.7%')

    await userEvent.type(screen.getByLabelText('التاريخ — الأحد إلى الأربعاء فقط'), '2026-09-06')
    await userEvent.type(screen.getByLabelText('عدد الصفحات — سبع صفحات فأكثر'), '10')
    await userEvent.type(screen.getByLabelText('اسم الكتاب'), 'كتاب التحضير')
    await userEvent.click(screen.getByRole('button', { name: 'إرسال للمراجعة' }))

    const call = globalThis.fetch.mock.calls.find(
      ([u, i]) => u.includes('/me/tahdir') && i?.method === 'POST',
    )
    expect(call).toBeTruthy()
  })

  it('الطالب: خطأ يوم الأسبوع يُعرض نصًّا كما وصل', async () => {
    mockApi({ role: 'pilot', submitOk: false })
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'تحضير القراءة' }))
    await screen.findByText('35.7%')

    await userEvent.type(screen.getByLabelText('التاريخ — الأحد إلى الأربعاء فقط'), '2026-09-10')
    await userEvent.type(screen.getByLabelText('عدد الصفحات — سبع صفحات فأكثر'), '10')
    await userEvent.type(screen.getByLabelText('اسم الكتاب'), 'كتاب')
    await userEvent.click(screen.getByRole('button', { name: 'إرسال للمراجعة' }))

    expect(await screen.findByText('تحضير القراءة يكون من الأحد إلى الأربعاء فقط.')).toBeInTheDocument()
  })

  it('المشرف: طابور تحضير القراءة يعرض الطلبات ويعتمد الكلّ', async () => {
    mockApi()
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'طابور تحضير القراءة' }))
    expect(await screen.findByRole('heading', { name: 'أحمد سالم' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /اعتماد الكلّ/ }))

    const call = globalThis.fetch.mock.calls.find(([u]) => u.includes('/admin/readings/approve'))
    expect(call).toBeTruthy()
  })

  it('المشرف: الإضافة المباشرة تعرض الساعات المُعادة من الخادم', async () => {
    mockApi()
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'طابور تحضير القراءة' }))
    await screen.findByRole('heading', { name: 'أحمد سالم' })

    await userEvent.selectOptions(screen.getByLabelText('الطالب'), '7')
    await userEvent.type(screen.getByLabelText('التاريخ — الأحد إلى الأربعاء فقط'), '2026-09-06')
    await userEvent.type(screen.getByLabelText('الصفحات'), '10')
    await userEvent.type(screen.getByLabelText('الكتاب'), 'تحضير مباشر')
    await userEvent.click(screen.getByRole('button', { name: 'إضافة' }))

    expect(await screen.findByText('10.00')).toBeInTheDocument()
  })

  it('المشرف: تقرير المنظمة يعرض النسبة والتعثّر كما وصلا', async () => {
    mockApi()
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'تقرير تحضير القراءة' }))
    expect(await screen.findByText('بندر الشمري')).toBeInTheDocument()
    expect(screen.getByText('أحمد سالم')).toBeInTheDocument()
    expect(screen.getAllByText('35.7%').length).toBeGreaterThan(0)
  })

  it('أزرار تحضير القراءة الإدارية لا تظهر لطيّار', async () => {
    mockApi({ role: 'pilot' })
    render(<App />)
    await screen.findByText('بندر الشمري')
    expect(screen.queryByRole('button', { name: 'طابور تحضير القراءة' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'تقرير تحضير القراءة' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'تحضير القراءة' })).toBeInTheDocument()
  })
})
