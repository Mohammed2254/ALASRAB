import { useState } from 'react'

import Placard, { Row } from '../components/Placard'
import { Async } from '../components/States'
import { api } from '../lib/api'
import { useAsync } from '../state/useAsync'

/*
  قراءاتي — إرسال طلب ومتابعة حالته.

  **كل رقم يأتي من الخادم.** `hours` تصل محسوبة من الحدث، ولا تُشتقّ هنا من
  `pages × وزن`: حسابها في مكانين يعني نسختين تتباعدان عند أوّل تعديل في
  الأوزان (`AGENTS.md` ٥).
*/

const STATUS = {
  pending: { label: 'قيد المراجعة', tone: 'muted' },
  approved: { label: 'معتمد', tone: 'taxi' },
  rejected: { label: 'مرفوض', tone: 'hold' },
}

const dayFormatter = new Intl.DateTimeFormat('ar-SA-u-ca-gregory-nu-latn', {
  day: 'numeric',
  month: 'long',
  timeZone: 'Asia/Riyadh',
})

const formatDay = (iso) => (iso ? dayFormatter.format(new Date(`${iso}T00:00:00Z`)) : null)

export default function MyReadings({ onDone }) {
  const state = useAsync(() => api.myReadings(), [])

  return (
    <div className="taxi-in mx-auto w-full max-w-[520px] px-4 pt-6 pb-10">
      <header className="mb-5 flex items-baseline gap-3">
        <h1 className="font-display text-[26px] leading-none">قراءاتي</h1>
        <span className="centerline" />
        <button
          type="button"
          onClick={onDone}
          className="min-h-[44px] shrink-0 px-2 text-[13px] text-muted"
        >
          رجوع
        </button>
      </header>

      <SubmitForm onSubmitted={state.reload} />

      <div className="mt-4">
        <Async state={state} loadingTitle="قراءاتي">
          {(data) => <History readings={data.readings} />}
        </Async>
      </div>
    </div>
  )
}

function SubmitForm({ onSubmitted }) {
  const [readOn, setReadOn] = useState('')
  const [pages, setPages] = useState('')
  const [book, setBook] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api.submitReading({ read_on: readOn, pages: Number(pages), book_title: book.trim() })
      setReadOn('')
      setPages('')
      setBook('')
      onSubmitted()
    } catch (err) {
      // الرسالة من الخادم كما هي: هو من يقرّر ما يُقال، وصياغتها هنا نسخة ثانية.
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const field = 'min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint'

  return (
    <Placard title="تسجيل قراءة">
      <form onSubmit={onSubmit} noValidate>
        <label htmlFor="read_on" className="mb-1.5 block text-[13px]">
          تاريخ القراءة
        </label>
        <input
          id="read_on"
          type="date"
          value={readOn}
          onChange={(e) => setReadOn(e.target.value)}
          className={`${field} mb-4`}
        />

        <label htmlFor="pages" className="mb-1.5 block text-[13px]">
          عدد الصفحات
        </label>
        <input
          id="pages"
          inputMode="numeric"
          value={pages}
          onChange={(e) => setPages(e.target.value)}
          className={`${field} mb-4`}
        />

        <label htmlFor="book" className="mb-1.5 block text-[13px]">
          اسم الكتاب
        </label>
        <input
          id="book"
          value={book}
          onChange={(e) => setBook(e.target.value)}
          className={field}
        />

        {error && (
          <p role="alert" className="mt-3 text-[13px] text-hold">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={busy || !readOn || !pages || !book.trim()}
          className="mt-5 min-h-[48px] w-full border border-taxi bg-taxi text-[16px] text-asphalt transition-opacity disabled:opacity-40"
        >
          {busy ? 'جارٍ الإرسال…' : 'إرسال للمراجعة'}
        </button>
      </form>

      <p className="mt-4 border-t border-concrete/35 pt-3 text-[12px] text-muted">
        لا تُحتسب الساعات قبل اعتماد المشرف.
      </p>
    </Placard>
  )
}

function History({ readings }) {
  if (readings.length === 0) {
    return (
      <Placard title="سجلّ طلباتي">
        <p className="py-2 text-[14px] text-muted">
          لم ترسل قراءةً بعد. أوّل طلب يبدأ سجلّك.
        </p>
      </Placard>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {readings.map((r) => {
        const badge = STATUS[r.status]
        return (
          <Placard key={r.id} title={r.book_title} aside={formatDay(r.read_on)}>
            <Row label="الحالة" value={badge.label} tone={badge.tone} />
            <Row label="الصفحات" value={<bdi dir="ltr">{r.pages}</bdi>} />
            {r.hours && (
              <Row label="الساعات" value={<bdi dir="ltr">{r.hours}</bdi>} tone="taxi" />
            )}
            {r.review_reason && (
              <p className="mt-2 border-t border-concrete/35 pt-2 text-[13px] text-hold">
                {r.review_reason}
              </p>
            )}
          </Placard>
        )
      })}
    </div>
  )
}
