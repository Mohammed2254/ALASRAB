import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '../App'

/*
  و-٨ — سلوك ملحوظ لا تفاصيل تنفيذ، بنفس منهج `admin-rules.test.jsx`.
*/

const PILOT = { user: { id: 1, full_name: 'بندر الشمري', student_no: '1001', role: 'pilot' } }
const ADMIN = { user: { id: 1, full_name: 'بندر الشمري', student_no: '1001', role: 'admin' } }
const DECK = {
  rank: { name: 'طيار أول', tier: 2 },
  hours: '611.25',
  next_rank: { name: 'رائد سرب', at_hours: '900.00', progress_pct: 42.3, remaining: '288.75' },
  flight: { grounded: false, last_activity_on: '2026-08-28' },
  team: { name: 'سرب الفرقان', rank_in_org: null },
}

const STATION_WITH_TEAM = {
  team: { name: 'سرب الفرقان', litres: '47.00' },
  tank_capacity_l: '500.00',
  recent: [
    { activity_name: 'الحفظ الجماعي', occurred_on: '2026-08-20', total_pct: '94.00', litres: '47.00' },
  ],
}

const STATION_NO_TEAM = { team: null, tank_capacity_l: null, recent: [] }

const ACTIVITIES = {
  activities: [
    {
      id: 1,
      key: 'group_memorize',
      name: 'الحفظ الجماعي',
      litres_full: '50.00',
      criteria: [
        { id: 1, key: 'attendance', name: 'الحضور', weight_pct: '40.00' },
        { id: 2, key: 'quality', name: 'الجودة', weight_pct: '60.00' },
      ],
    },
  ],
}

const TEAMS = {
  teams: [{ id: 1, name: 'سرب الفرقان', code: 'FRQ', archived_at: null, active_members: 4 }],
}

function mockApi({ identity = PILOT, station = STATION_WITH_TEAM, activities = ACTIVITIES, teams = TEAMS } = {}) {
  globalThis.fetch = vi.fn(async (url, opts = {}) => {
    const ok = (json) => ({ ok: true, status: 200, json: async () => json })
    if (url.includes('/auth/me')) return ok(identity)
    if (url.includes('/me/deck')) return ok(DECK)
    if (url.includes('/me/events')) return ok({ events: [] })
    if (url.includes('/station')) return ok(station)
    if (url.includes('/admin/fuel/activities') && opts.method === 'POST') return { ok: true, status: 201, json: async () => ({ id: 2 }) }
    if (url.includes('/admin/fuel/activities')) return ok(activities)
    if (url.includes('/admin/fuel/assess'))
      return { ok: true, status: 201, json: async () => ({ id: 9, total_pct: '94.00', litres: '47.00' }) }
    if (url.includes('/admin/teams')) return ok(teams)
    return { ok: false, status: 404, json: async () => ({ message: 'غير متوقَّع' }) }
  })
}

beforeEach(() => vi.restoreAllMocks())

describe('محطة التزوّد — و-٨', () => {
  it('تظهر لكل طيّار — لا للمشرف وحده', async () => {
    mockApi({ identity: PILOT })
    render(<App />)
    expect(await screen.findByRole('button', { name: 'محطة التزوّد' })).toBeInTheDocument()
  })

  it('تعرض لترات السرب وسعة الخزّان وآخر تقييم', async () => {
    mockApi({ identity: PILOT })
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'محطة التزوّد' }))
    expect(await screen.findAllByText('47.00')).not.toHaveLength(0)
    expect(screen.getByText('500.00')).toBeInTheDocument()
    expect(screen.getByText('الحفظ الجماعي')).toBeInTheDocument()
  })

  it('حالة بلا سرب مصمَّمة لا شاشة معطوبة', async () => {
    mockApi({ identity: PILOT, station: STATION_NO_TEAM })
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'محطة التزوّد' }))
    expect(await screen.findByText('لست في سرب حاليًّا. راجع المشرف.')).toBeInTheDocument()
  })

  it('أزرار إدارة الوقود لا تظهر لطيّار', async () => {
    mockApi({ identity: PILOT })
    render(<App />)
    await screen.findByRole('button', { name: 'محطة التزوّد' })
    expect(screen.queryByRole('button', { name: 'أنشطة الوقود' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'تقييم نشاط' })).not.toBeInTheDocument()
  })
})

describe('أنشطة الوقود — و-٨', () => {
  it('تعرض الأنشطة القائمة وبنودها', async () => {
    mockApi({ identity: ADMIN })
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'أنشطة الوقود' }))
    expect(await screen.findByText('الحضور')).toBeInTheDocument()
    expect(screen.getByText('40.00٪')).toBeInTheDocument()
  })
})

describe('تقييم نشاط — و-٨', () => {
  it('يعرض بنود النشاط المختار ويحسب النتيجة من ردّ الخادم', async () => {
    mockApi({ identity: ADMIN })
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'تقييم نشاط' }))

    await userEvent.selectOptions(await screen.findByLabelText('السرب'), '1')
    await userEvent.selectOptions(screen.getByLabelText('النشاط'), '1')
    expect(await screen.findByLabelText('درجة الحضور')).toBeInTheDocument()

    await userEvent.type(screen.getByLabelText('تاريخ الوقوع'), '2026-08-20')
    await userEvent.type(screen.getByLabelText('درجة الحضور'), '100')
    await userEvent.type(screen.getByLabelText('درجة الجودة'), '90')
    await userEvent.click(screen.getByRole('button', { name: 'حفظ التقييم' }))

    expect(await screen.findByText(/47.00 لتر/)).toBeInTheDocument()
  })
})
