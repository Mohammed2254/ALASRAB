import { useState, type FormEvent } from 'react'

import { api, ApiError } from '../api'
import { fmtDecimal } from '../api/format'
import { useAsync } from '../state/useAsync'
import { Async } from '../ui/Async'
import Button from '../ui/Button'
import EmptyState from '../ui/EmptyState'
import Field from '../ui/Field'
import Pill from '../ui/Pill'
import Placard from '../ui/Placard'
import Prow from '../ui/Prow'

/**
 * قراءاتي — إرسال طلب ومتابعة حالته (`GET`/`POST /me/readings`، FR-020..024).
 * **كل رقم من الخادم:** `hours` تصل محسوبة من الحدث بعد الاعتماد، ولا تُشتقّ
 * هنا من `pages × وزن` (`AGENTS.md` ٥).
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
      await api.me.submitReading({ read_on: readOn, pages, book_title: book.trim() })
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

  const fieldClass =
    'min-h-[48px] w-full rounded-(--radius-sm) border border-(--color-border-strong) bg-(--color-bg-2) px-3 text-[16px] text-(--color-text)'

  return (
    <Placard title="تسجيل قراءة">
      <form onSubmit={onSubmit} noValidate>
        <Field label="تاريخ القراءة" htmlFor="read_on">
          <input id="read_on" type="date" value={readOn} onChange={(e) => setReadOn(e.target.value)} className={fieldClass} />
        </Field>
        <Field label="عدد الصفحات" htmlFor="pages">
          <input id="pages" inputMode="numeric" value={pages} onChange={(e) => setPages(e.target.value)} className={fieldClass} />
        </Field>
        <Field label="اسم الكتاب" htmlFor="book">
          <input id="book" value={book} onChange={(e) => setBook(e.target.value)} className={fieldClass} />
        </Field>

        {error ? (
          <p role="alert" className="mb-4 text-[13px] text-(--color-red-text)">
            {error}
          </p>
        ) : null}

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

export default function Readings() {
  const state = useAsync(() => api.me.readings(), [])

  return (
    <div className="flex flex-col gap-3.5">
      <SubmitForm onSubmitted={state.reload} />

      <Async state={state} loadingTitle="قراءاتي">
        {(data) =>
          data.readings.length === 0 ? (
            <Placard title="سجلّ طلباتي">
              <EmptyState>لم ترسل قراءةً بعد. أوّل طلب يبدأ سجلّك.</EmptyState>
            </Placard>
          ) : (
            <div className="flex flex-col gap-3.5">
              {data.readings.map((r) => {
                const badge = STATUS[r.status] ?? STATUS.pending!
                return (
                  <Placard key={r.id} title={r.book_title} aside={formatDay(r.read_on)}>
                    <Prow label="الحالة" value={<Pill tone={badge.tone} size="sm">{badge.label}</Pill>} />
                    <Prow label="الصفحات" value={<bdi dir="ltr">{r.pages}</bdi>} />
                    {r.hours ? <Prow label="الساعات" value={<bdi dir="ltr">{fmtDecimal(r.hours)}</bdi>} tone="accent" /> : null}
                    {r.review_reason ? (
                      <p className="mt-2 border-t border-(--color-border) pt-2 text-[13px] text-(--color-red-text)">
                        {r.review_reason}
                      </p>
                    ) : null}
                  </Placard>
                )
              })}
            </div>
          )
        }
      </Async>
    </div>
  )
}
