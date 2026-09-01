import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '../App'

/*
  و-٧ — سلوك ملحوظ لا تفاصيل تنفيذ، بنفس منهج `deck.test.jsx`: `fetch` وحده
  مُستبدَل، وردوده منسوخة من عقد `API.md` الحقيقي.
*/

const ADMIN = { user: { id: 1, full_name: 'بندر الشمري', student_no: '1001', role: 'admin' } }
const DECK = {
  rank: { name: 'طيار أول', tier: 2 },
  hours: '611.25',
  next_rank: { name: 'رائد سرب', at_hours: '900.00', progress_pct: 42.3, remaining: '288.75' },
  flight: { grounded: false, last_activity_on: '2026-08-28' },
  team: { name: 'سرب الفرقان', rank_in_org: null },
}

const WEIGHTS = {
  current: {
    id: 3,
    effective_from: '2026-09-01T00:00:00Z',
    note: 'معايرة سبتمبر',
    weights: [{ activity_type: 'memorize', hours_per_unit: '2.5000' }],
    multipliers: [{ grade: 'mastered', multiplier: '1.500' }],
  },
  history: [{ id: 2, effective_from: '2020-01-01T00:00:00Z', note: null }],
}

const THRESHOLDS = {
  thresholds: [
    { key: 'trainee', name: 'طيار', tier: 1, at_hours: '0.00' },
    { key: 'pilot1', name: 'طيار أول', tier: 2, at_hours: '400.00' },
  ],
}

const TEAMS = {
  teams: [{ id: 1, name: 'سرب الفرقان', code: 'FRQ', archived_at: null, active_members: 4 }],
}

function mockApi({ deck = DECK, weights = WEIGHTS, thresholds = THRESHOLDS, teams = TEAMS, audit = { entries: [] } } = {}) {
  globalThis.fetch = vi.fn(async (url) => {
    const ok = (json) => ({ ok: true, status: 200, json: async () => json })
    if (url.includes('/auth/me')) return ok(ADMIN)
    if (url.includes('/me/deck')) return ok(deck)
    if (url.includes('/me/events')) return ok({ events: [] })
    if (url.includes('/admin/weights')) return ok(weights)
    if (url.includes('/admin/thresholds/preview'))
      return ok({ promoted: [], demoted: [], warning: null })
    if (url.includes('/admin/thresholds')) return ok(thresholds)
    if (url.includes('/admin/teams')) return ok(teams)
    if (url.includes('/admin/audit')) return ok(audit)
    return { ok: false, status: 404, json: async () => ({ message: 'غير متوقَّع' }) }
  })
}

beforeEach(() => vi.restoreAllMocks())

describe('نافذة المشرف — و-٧', () => {
  it('الأوزان: تعرض الإصدار الساري كما وصل', async () => {
    mockApi()
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'الأوزان' }))
    expect(await screen.findByText('memorize')).toBeInTheDocument()
    expect(screen.getByText('2.5000')).toBeInTheDocument()
  })

  it('العتبات: المعاينة تعرض «لا أحد يتراجع» — لا حساب في الواجهة', async () => {
    mockApi()
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'العتبات' }))
    await screen.findByDisplayValue('طيار')
    await userEvent.click(screen.getByRole('button', { name: 'معاينة الأثر' }))
    expect(await screen.findByText('لا أحد يرتفع بهذا التغيير.')).toBeInTheDocument()
    expect(screen.getByText(/لا أحد يتراجع أبدًا/)).toBeInTheDocument()
  })

  it('الأسراب: تعرض السرب القائم وعدد أعضائه', async () => {
    mockApi()
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'الأسراب' }))
    expect(await screen.findByText('سرب الفرقان (FRQ)')).toBeInTheDocument()
    expect(screen.getByText('4 عضو')).toBeInTheDocument()
  })

  it('سجلّ التغييرات: الحالة الفارغة صريحة لا شاشة معطوبة', async () => {
    mockApi()
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'سجلّ التغييرات' }))
    expect(await screen.findByText('لا تغييرات بعد.')).toBeInTheDocument()
  })

  it('سجلّ التغييرات: صفٌّ حقيقي يعرض الفاعل والملخّص', async () => {
    mockApi({
      audit: {
        entries: [
          {
            id: 41,
            kind: 'thresholds_update',
            summary: 'تحديث سُلّم الرتب',
            actor_name: 'بندر الشمري',
            at: '2026-09-01T12:00:00Z',
          },
        ],
      },
    })
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'سجلّ التغييرات' }))
    expect(await screen.findByText('تحديث سُلّم الرتب')).toBeInTheDocument()
    expect(screen.getByText('بواسطة بندر الشمري')).toBeInTheDocument()
  })

  it('زرّ الأوزان لا يظهر لطيار', async () => {
    mockApi({ deck: DECK })
    globalThis.fetch = vi.fn(async (url) => {
      const ok = (json) => ({ ok: true, status: 200, json: async () => json })
      if (url.includes('/auth/me'))
        return ok({ user: { ...ADMIN.user, role: 'pilot' } })
      if (url.includes('/me/deck')) return ok(DECK)
      if (url.includes('/me/events')) return ok({ events: [] })
      return { ok: false, status: 404, json: async () => ({}) }
    })
    render(<App />)
    await screen.findByText('بندر الشمري')
    expect(screen.queryByRole('button', { name: 'الأوزان' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'سجلّ التغييرات' })).not.toBeInTheDocument()
  })
})
