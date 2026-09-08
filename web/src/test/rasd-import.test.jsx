import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '../App'

/*
  استيراد راصد — و-٥. سلوك ملحوظ لا تفاصيل تنفيذ، نفس منهج
  `tahdir.test.jsx`/`quran-edit.test.jsx`.
*/

const ADMIN = { user: { id: 1, full_name: 'بندر الشمري', student_no: '1001', role: 'admin' } }
const DECK = {
  rank: { name: 'طيار أول', tier: 2 },
  hours: '611.25',
  next_rank: { name: 'رائد سرب', at_hours: '900.00', progress_pct: 42.3, remaining: '288.75' },
  flight: { grounded: false, last_activity_on: '2026-08-28' },
  team: { name: 'سرب الفرقان', rank_in_org: null },
}
const STUDENTS = {
  students: [
    { id: 7, full_name: 'أحمد سالم' },
    { id: 8, full_name: 'سالم أحمد' },
  ],
}
const PREVIEW = {
  batch_id: 'abc123',
  duplicate_warning: false,
  duplicate_imported_at: null,
  rows: [
    {
      name: 'أحمد سالم',
      match_status: 'matched',
      user_id: 7,
      candidate_ids: [],
      percentages: { hifz: '61.5', thabat: '406.5', muraja3a: '53.6' },
      attendance: '2',
      tasmi3_days: '2',
    },
    {
      name: 'مجهول الاسم',
      match_status: 'unmatched',
      user_id: null,
      candidate_ids: [],
      percentages: { hifz: '0.0', thabat: '0.0', muraja3a: '0.0' },
      attendance: '0',
      tasmi3_days: '0',
    },
  ],
}
const COMMIT_RESULT = {
  batch_id: 'abc123',
  events_created: 4,
  rows: [
    { name: 'أحمد سالم', status: 'resolved', user_id: 7 },
    { name: 'مجهول الاسم', status: 'unmatched', user_id: null },
  ],
}

function mockApi({ role = 'admin' } = {}) {
  globalThis.fetch = vi.fn(async (url) => {
    const ok = (json, status = 200) => ({ ok: true, status, json: async () => json })
    if (url.includes('/auth/me')) return ok({ user: { ...ADMIN.user, role } })
    if (url.includes('/me/deck')) return ok(DECK)
    if (url.includes('/me/events')) return ok({ events: [] })
    if (url.includes('/admin/quran/students')) return ok(STUDENTS)
    if (url.includes('/admin/paste/preview')) return ok(PREVIEW)
    if (url.includes('/admin/paste/commit')) return ok(COMMIT_RESULT, 201)
    return { ok: false, status: 404, json: async () => ({ message: 'غير متوقَّع' }) }
  })
}

function csvFile() {
  return new File(['الطالب,...'], 'rasd.csv', { type: 'text/csv' })
}

beforeEach(() => vi.restoreAllMocks())

describe('استيراد راصد — و-٥', () => {
  it('المشرف: المعاينة تعرض النسب وحالة المطابقة كما وصلت — لا حساب هنا', async () => {
    mockApi()
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'استيراد راصد' }))

    await userEvent.upload(screen.getByLabelText('ملفّ CSV من راصد'), csvFile())
    await userEvent.type(screen.getByLabelText('تاريخ الوقوع'), '2026-08-02')
    await userEvent.click(screen.getByRole('button', { name: 'معاينة' }))

    expect(await screen.findByText('61.5%')).toBeInTheDocument()
    expect(screen.getByText('406.5%')).toBeInTheDocument()
    expect(screen.getByText('مطابَق')).toBeInTheDocument()
    expect(screen.getByText('غير مطابَق')).toBeInTheDocument()
  })

  it('المشرف: الاسم غير المطابَق يعرض قائمة اختيار طالب — لا تخمين تلقائيّ', async () => {
    mockApi()
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'استيراد راصد' }))
    await userEvent.upload(screen.getByLabelText('ملفّ CSV من راصد'), csvFile())
    await userEvent.type(screen.getByLabelText('تاريخ الوقوع'), '2026-08-02')
    await userEvent.click(screen.getByRole('button', { name: 'معاينة' }))
    await screen.findByText('غير مطابَق')

    expect(
      screen.getByLabelText('اختر الطالب الصحيح — لن يُستورَد بلا اختيار')
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /سيُستبعَد 1/ })).toBeInTheDocument()
  })

  it('المشرف: الاعتماد يرسل الملفّ نفسه ويعرض نتيجة الخادم كما وصلت', async () => {
    mockApi()
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'استيراد راصد' }))
    await userEvent.upload(screen.getByLabelText('ملفّ CSV من راصد'), csvFile())
    await userEvent.type(screen.getByLabelText('تاريخ الوقوع'), '2026-08-02')
    await userEvent.click(screen.getByRole('button', { name: 'معاينة' }))
    await screen.findByText('مطابَق')

    await userEvent.click(screen.getByRole('button', { name: /اعتماد الاستيراد/ }))

    expect(await screen.findByText('4 حدثًا جديدًا')).toBeInTheDocument()
    const call = globalThis.fetch.mock.calls.find(([u]) => u.includes('/admin/paste/commit'))
    expect(call).toBeTruthy()
    expect(call[1].body).toBeInstanceOf(FormData)
  })

  it('زرّ استيراد راصد لا يظهر لطيّار', async () => {
    mockApi({ role: 'pilot' })
    render(<App />)
    await screen.findByText('بندر الشمري')
    expect(screen.queryByRole('button', { name: 'استيراد راصد' })).not.toBeInTheDocument()
  })
})
