import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '../App'

/*
  سلوك ملحوظ لا تفاصيل تنفيذ.

  `fetch` وحده مُستبدَل — وهو **حدّ الشبكة** لا منطق المجال. الردود أدناه منسوخة
  من ردود الخادم الحقيقية المتحقَّق منها في Part 4، فلو تغيّر العقد سقطت هذه
  الاختبارات — وهذا هو المطلوب.
*/

const IDENTITY = { user: { id: 1, full_name: 'بندر الشمري', student_no: '1001', role: 'pilot' } }

const NORMAL = {
  rank: { name: 'طيار أول', tier: 2 },
  hours: '611.25',
  next_rank: { name: 'رائد سرب', at_hours: '900.00', progress_pct: 42.3, remaining: '288.75' },
  flight: { grounded: false, last_activity_on: '2026-08-28' },
  team: { name: 'سرب الفرقان', rank_in_org: null },
}

const EMPTY = {
  rank: { name: 'طيار', tier: 1 },
  hours: '0.00',
  next_rank: { name: 'طيار أول', at_hours: '400.00', progress_pct: 0.0, remaining: '400.00' },
  flight: { grounded: false, last_activity_on: null },
  team: { name: 'سرب الفرقان', rank_in_org: null },
}

const MAX_RANK = { ...NORMAL, rank: { name: 'قائد', tier: 4 }, hours: '1560.00', next_rank: null }
const GROUNDED = { ...NORMAL, flight: { grounded: true, last_activity_on: '2026-07-31' } }
const NO_TEAM = { ...NORMAL, team: null }

/** ردّ واحد لكل مسار — أبسط من طابور، ويكشف الطلب غير المتوقَّع. */
function mockApi({ me = IDENTITY, deck = NORMAL, meStatus = 200, deckStatus = 200 } = {}) {
  globalThis.fetch = vi.fn(async (url, opts = {}) => {
    const json = async () => (url.includes('/me/deck') ? deck : me)
    if (url.includes('/auth/logout')) return { ok: true, status: 204, json }
    if (url.includes('/auth/login')) {
      return opts.method === 'POST' && JSON.parse(opts.body).pin === '1234'
        ? { ok: true, status: 200, json: async () => IDENTITY }
        : { ok: false, status: 401, json: async () => ({ message: 'رقم الطالب أو الرمز غير صحيح.' }) }
    }
    if (url.includes('/me/deck'))
      return { ok: deckStatus === 200, status: deckStatus, json }
    return { ok: meStatus === 200, status: meStatus, json }
  })
}

beforeEach(() => vi.restoreAllMocks())

describe('البوّابة', () => {
  it('تعرض شاشة الدخول لمن ليس داخلًا', async () => {
    mockApi({ meStatus: 401 })
    render(<App />)
    expect(await screen.findByRole('button', { name: 'دخول' })).toBeInTheDocument()
  })

  it('لا تومض شاشة الدخول لمن هو داخل أصلًا', async () => {
    mockApi()
    render(<App />)
    // أوّل رسمة قبل جواب الخادم: تحقّق لا دخول.
    expect(screen.getByText('جارٍ التحقّق')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'دخول' })).not.toBeInTheDocument()
    await screen.findByText('بندر الشمري')
  })
})

describe('الدخول', () => {
  it('ينقل إلى البطاقة عند نجاحه', async () => {
    mockApi({ meStatus: 401 })
    render(<App />)
    await screen.findByRole('button', { name: 'دخول' })

    globalThis.fetch.mockClear()
    mockApi()  // بعد الدخول تصير الجلسة قائمة
    await userEvent.type(screen.getByLabelText('رقم الطالب'), '1001')
    await userEvent.type(screen.getByLabelText('الرمز (أربعة أرقام)'), '1234')
    await userEvent.click(screen.getByRole('button', { name: 'دخول' }))

    expect(await screen.findByText('بندر الشمري')).toBeInTheDocument()
  })

  it('يعرض رسالة الخادم العامّة عند الفشل — بلا كشف وجود الرقم', async () => {
    mockApi({ meStatus: 401 })
    render(<App />)
    await screen.findByRole('button', { name: 'دخول' })

    await userEvent.type(screen.getByLabelText('رقم الطالب'), '9999')
    await userEvent.type(screen.getByLabelText('الرمز (أربعة أرقام)'), '0000')
    await userEvent.click(screen.getByRole('button', { name: 'دخول' }))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('رقم الطالب أو الرمز غير صحيح.')
    expect(alert.textContent).not.toMatch(/غير موجود|غير مسجّل|الرمز خاطئ/)
  })

  it('لا يطلب رقم منظمة', async () => {
    mockApi({ meStatus: 401 })
    render(<App />)
    await screen.findByRole('button', { name: 'دخول' })
    expect(screen.queryByLabelText(/منظمة|جمعية|org/i)).not.toBeInTheDocument()
    expect(screen.getAllByRole('textbox').length + 1).toBe(2)  // رقم + رمز (password)
  })
})

describe('البطاقة', () => {
  it('تعرض قيم الخادم كما وصلت', async () => {
    mockApi()
    render(<App />)
    expect(await screen.findByText('611.25')).toBeInTheDocument()
    expect(screen.getByText('طيار أول')).toBeInTheDocument()
    expect(screen.getByText('42.3%')).toBeInTheDocument()
    expect(screen.getByText('288.75')).toBeInTheDocument()
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '42.3')
  })

  it('الحالة الفارغة مصمَّمة لا مكسورة', async () => {
    mockApi({ deck: EMPTY })
    render(<App />)
    expect(await screen.findByText('0.00')).toBeInTheDocument()
    expect(screen.getByText('طيار')).toBeInTheDocument()
    expect(screen.getByText('لا نشاط بعد')).toBeInTheDocument()
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0')
  })

  it('أعلى رتبة: رسالة إتمام لا شريط ممتلئ', async () => {
    mockApi({ deck: MAX_RANK })
    render(<App />)
    expect(await screen.findByText('بلغتَ أعلى رتبة.')).toBeInTheDocument()
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
  })

  it('الحالة الأرضية بشكل ونصّ معًا لا بلون وحده', async () => {
    mockApi({ deck: GROUNDED })
    render(<App />)
    // النصّ يقرؤه من لا يميّز الأحمر، ويذكر الفعل التالي لا التوبيخ.
    expect(await screen.findByText('أرضي')).toBeInTheDocument()
    // الشكل لا يعتمد على خطّ إيموجي: SVG يُرسَم دائمًا.
    expect(document.querySelector('svg rect[fill="currentColor"]')).toBeTruthy()
    expect(screen.getByText(/سجّل قراءةً أو حفظًا جديدًا/)).toBeInTheDocument()
  })

  it('ترتيب السرب غير المتاح يُعرض ولا يُحسب', async () => {
    mockApi()
    render(<App />)
    expect(await screen.findByText('غير متاح بعد')).toBeInTheDocument()
  })

  it('غياب السرب لا يكسر الشاشة', async () => {
    mockApi({ deck: NO_TEAM })
    render(<App />)
    expect(await screen.findByText('لست في سرب حاليًّا. راجع المشرف.')).toBeInTheDocument()
    expect(screen.getByText('611.25')).toBeInTheDocument()
  })
})

describe('الأعطال', () => {
  it('انقطاع الشبكة يُشرح ويُعرض معه زرّ إعادة', async () => {
    globalThis.fetch = vi.fn(async () => { throw new TypeError('network') })
    render(<App />)
    expect(await screen.findByText(/تعذّر الوصول إلى الخادم/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'إعادة المحاولة' })).toBeInTheDocument()
  })

  it('عطل الخادم لا يعرض تفاصيل داخلية', async () => {
    mockApi({ deckStatus: 500, deck: { message: 'حدث خلل في الخادم. حاول بعد قليل.' } })
    render(<App />)
    const failure = await screen.findByText('حدث خلل في الخادم. حاول بعد قليل.')
    expect(failure).toBeInTheDocument()
    expect(document.body.textContent).not.toMatch(/Traceback|SELECT|rank_thresholds/)
  })
})

describe('الخروج', () => {
  it('يعيد إلى شاشة الدخول', async () => {
    mockApi()
    render(<App />)
    await screen.findByText('بندر الشمري')
    await userEvent.click(screen.getByRole('button', { name: 'خروج' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'دخول' })).toBeInTheDocument())
  })
})

describe('العربية والعرض', () => {
  it('نظام أرقام واحد في الشاشة — لا خلط بين اللاتيني والعربي-الهندي', async () => {
    /*
      `SCOPE.md` §١٠.٣. الساعات تصل نصًّا لاتينيًّا من الخادم، فلو نسّقنا التاريخ
      بـ`ar-SA` وحدها لظهر «٢٨ أغسطس» بجوار «611.25» — نظامان في نظرة واحدة.
    */
    mockApi()
    render(<App />)
    await screen.findByText('611.25')
    expect(document.body.textContent).not.toMatch(/[٠-٩]/)
  })

  it('لا تباعد حروف على العربية — يكسر وصلها', async () => {
    mockApi()
    render(<App />)
    const name = await screen.findByText('بندر الشمري')
    expect(name.className).not.toMatch(/tracking-|tracked/)
  })
})
