import { useState } from 'react'

import Placard, { Row } from '../components/Placard'
import { Async } from '../components/States'
import { api } from '../lib/api'
import { useAsync } from '../state/useAsync'

/*
  تحضير القراءة — و-١١ · FR-090..093.

  نفس شكل «قراءاتي» تمامًا (طلب معلَّق ← اعتماد ← ساعات)، ببرنامج مستقلّ
  وحدّ أدنى ٧ صفحات والأحد–الأربعاء حصرًا. **كل رقم في التقرير الأسبوعي
  (الأيام · النسبة · «متعثّر») يصل محسوبًا من الخادم** — لا حساب هنا
  (AGENTS ٥).
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

export default function Tahdir({ onDone }) {
  const state = useAsync(() => api.myTahdir(), [])

  return (
    <div className="taxi-in mx-auto w-full max-w-[520px] px-4 pt-6 pb-10">
      <header className="mb-5 flex items-baseline gap-3">
        <h1 className="font-display text-[26px] leading-none">تحضير القراءة</h1>
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
        <Async state={state} loadingTitle="تحضير القراءة">
          {(data) => (
            <div className="flex flex-col gap-4">
              <WeekCard week={data.week} />
              <History submissions={data.submissions} />
            </div>
          )}
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
      await api.submitTahdir({ read_on: readOn, pages: Number(pages), book_title: book.trim() })
      setReadOn('')
      setPages('')
      setBook('')
      onSubmitted()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const field = 'min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint'

  return (
    <Placard title="تحضير اليوم">
      <form onSubmit={onSubmit} noValidate>
        <label htmlFor="td_read_on" className="mb-1.5 block text-[13px]">
          التاريخ — الأحد إلى الأربعاء فقط
        </label>
        <input
          id="td_read_on"
          type="date"
          value={readOn}
          onChange={(e) => setReadOn(e.target.value)}
          className={`${field} mb-4`}
        />

        <label htmlFor="td_pages" className="mb-1.5 block text-[13px]">
          عدد الصفحات — سبع صفحات فأكثر
        </label>
        <input
          id="td_pages"
          inputMode="numeric"
          value={pages}
          onChange={(e) => setPages(e.target.value)}
          className={`${field} mb-4`}
        />

        <label htmlFor="td_book" className="mb-1.5 block text-[13px]">
          اسم الكتاب
        </label>
        <input
          id="td_book"
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

function WeekCard({ week }) {
  return (
    <Placard title="أسبوعي الحاليّ" aside={week.struggling ? 'متعثّر' : 'على المسار'}>
      {week.days.map((d) => (
        <Row
          key={d.date}
          label={d.weekday}
          value={d.completed ? 'مكتمل ✓' : <bdi dir="ltr">{d.pages}</bdi>}
          tone={d.completed ? 'taxi' : 'muted'}
        />
      ))}
      <div className="mt-2 border-t border-concrete/35 pt-2">
        <Row
          label="المجموع"
          value={
            <span>
              <bdi dir="ltr">{week.pages_total}</bdi> / <bdi dir="ltr">{week.target_pages}</bdi>
            </span>
          }
        />
        <Row
          label="النسبة"
          value={<bdi dir="ltr">{week.percent}%</bdi>}
          tone={week.struggling ? 'hold' : 'taxi'}
        />
      </div>
    </Placard>
  )
}

function History({ submissions }) {
  if (submissions.length === 0) {
    return (
      <Placard title="سجلّ تحضيري">
        <p className="py-2 text-[14px] text-muted">لم تُحضّر بعد. أوّل طلب يبدأ سجلّك.</p>
      </Placard>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {submissions.map((s) => {
        const badge = STATUS[s.status]
        return (
          <Placard key={s.id} title={s.book_title} aside={formatDay(s.read_on)}>
            <Row label="الحالة" value={badge.label} tone={badge.tone} />
            <Row label="الصفحات" value={<bdi dir="ltr">{s.pages}</bdi>} />
            {s.hours && <Row label="الساعات" value={<bdi dir="ltr">{s.hours}</bdi>} tone="taxi" />}
            {s.review_reason && (
              <p className="mt-2 border-t border-concrete/35 pt-2 text-[13px] text-hold">
                {s.review_reason}
              </p>
            )}
          </Placard>
        )
      })}
    </div>
  )
}
