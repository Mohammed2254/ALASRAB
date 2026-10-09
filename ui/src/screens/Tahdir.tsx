import { useState, type FormEvent } from 'react'

import { api, ApiError } from '../api'
import { fmtDecimal } from '../api/format'
import { go } from '../nav/history'
import { useAsync } from '../state/useAsync'
import { Async } from '../ui/Async'
import Button from '../ui/Button'
import EmptyState from '../ui/EmptyState'
import Field, { fieldClass } from '../ui/Field'
import Pill from '../ui/Pill'
import Placard from '../ui/Placard'
import Prow from '../ui/Prow'
import Subback from '../ui/Subback'
import ErrorText from '../ui/ErrorText'

/**
 * تحضير القراءة — `GET`/`POST /me/tahdir` (FR-090..093). نفس شكل «قراءاتي»
 * تمامًا (طلب معلَّق ← اعتماد ← ساعات)، ببرنامج مستقلّ وبطاقة أسبوع إضافية.
 * **كل رقم في التقرير الأسبوعي يصل محسوبًا من الخادم** — لا حساب هنا
 * (`AGENTS.md` ٥). `percent`/`pages_total`/`target_pages` رقمية لا عشرية،
 * تُطبع مباشرةً بلا `fmtDecimal` (`و-١٦.md` §١.١).
 */

const STATUS: Record<string, { label: string; tone: 'muted' | 'accent' | 'red' }> = {
  pending: { label: 'قيد المراجعة', tone: 'muted' },
  approved: { label: 'معتمد', tone: 'accent' },
  rejected: { label: 'مرفوض', tone: 'red' },
}

const dayFormatter = new Intl.DateTimeFormat('ar-SA-u-ca-gregory-nu-latn', {
  day: 'numeric',
  month: 'long',
  timeZone: 'Asia/Riyadh',
})
const formatDay = (iso: string) => dayFormatter.format(new Date(`${iso}T00:00:00Z`))

function SubmitForm({ onSubmitted }: { onSubmitted: () => void }) {
  const [readOn, setReadOn] = useState('')
  const [pages, setPages] = useState('')
  const [book, setBook] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api.me.submitTahdir({ read_on: readOn, pages, book_title: book.trim() })
      setReadOn('')
      setPages('')
      setBook('')
      onSubmitted()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
    } finally {
      setBusy(false)
    }
  }


  return (
    <Placard title="تحضير جديد">
      <form onSubmit={onSubmit} noValidate>
        <Field label="التاريخ — الأحد إلى الأربعاء فقط" htmlFor="td_read_on">
          <input id="td_read_on" type="date" value={readOn} onChange={(e) => setReadOn(e.target.value)} className={fieldClass} />
        </Field>
        <Field label="عدد الصفحات — سبع صفحات فأكثر" htmlFor="td_pages">
          <input id="td_pages" inputMode="numeric" value={pages} onChange={(e) => setPages(e.target.value)} className={fieldClass} />
        </Field>
        <Field label="اسم الكتاب" htmlFor="td_book">
          <input id="td_book" value={book} onChange={(e) => setBook(e.target.value)} className={fieldClass} />
        </Field>

        {error ? <ErrorText spacing="mb-4">{error}</ErrorText> : null}

        <Button type="submit" disabled={busy || !readOn || !pages || !book.trim()} className="w-full">
          {busy ? 'جارٍ الإرسال…' : 'إرسال للمراجعة'}
        </Button>
      </form>

      <p className="mt-4 border-t border-(--color-border) pt-3 text-[12px] text-(--color-text-dim)">
        لا تُحتسب الساعات قبل اعتماد المشرف.
      </p>
    </Placard>
  )
}

export default function Tahdir() {
  const state = useAsync(() => api.me.tahdir(), [])

  return (
    <div className="flex flex-col gap-3.5">
      <Subback label="الرئيسية" onClick={() => go('deck')} />
      <SubmitForm onSubmitted={state.reload} />

      <Async state={state} loadingTitle="تحضير القراءة">
        {(data) => (
          <>
            <Placard title="تحضيراتي هذا الأسبوع" aside={data.week.struggling ? 'متعثّر' : 'على المسار'}>
              {data.week.days.map((d) => (
                <Prow
                  key={d.date}
                  label={d.weekday}
                  value={d.completed ? 'مكتمل ✓' : <bdi dir="ltr">{d.pages}</bdi>}
                  tone={d.completed ? 'accent' : undefined}
                />
              ))}
              <div className="mt-2 border-t border-(--color-border) pt-2">
                <Prow
                  label="المجموع"
                  value={
                    <span>
                      <bdi dir="ltr">{data.week.pages_total}</bdi> / <bdi dir="ltr">{data.week.target_pages}</bdi>
                    </span>
                  }
                />
                <Prow
                  label="النسبة"
                  value={<bdi dir="ltr">{data.week.percent}%</bdi>}
                  tone={data.week.struggling ? 'red' : 'accent'}
                />
              </div>
            </Placard>

            {data.submissions.length === 0 ? (
              <Placard title="سجلّ تحضيري">
                <EmptyState>لم تُحضّر بعد. أوّل طلب يبدأ سجلّك.</EmptyState>
              </Placard>
            ) : (
              <div className="flex flex-col gap-3.5">
                {data.submissions.map((s) => {
                  const badge = STATUS[s.status] ?? STATUS.pending!
                  return (
                    <Placard key={s.id} title={s.book_title} aside={formatDay(s.read_on)}>
                      <Prow label="الحالة" value={<Pill tone={badge.tone} size="sm">{badge.label}</Pill>} />
                      <Prow label="الصفحات" value={<bdi dir="ltr">{s.pages}</bdi>} />
                      {s.hours ? <Prow label="الساعات" value={<bdi dir="ltr">{fmtDecimal(s.hours)}</bdi>} tone="accent" /> : null}
                      {s.review_reason ? (
                        <p className="mt-2 border-t border-(--color-border) pt-2 text-[13px] text-(--color-red-text)">
                          {s.review_reason}
                        </p>
                      ) : null}
                    </Placard>
                  )
                })}
              </div>
            )}
          </>
        )}
      </Async>
    </div>
  )
}
