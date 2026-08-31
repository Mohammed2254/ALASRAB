import { useState } from 'react'

import Placard, { Row } from '../../components/Placard'
import { Async } from '../../components/States'
import { api } from '../../lib/api'
import { useAsync } from '../../state/useAsync'

/*
  طابور اعتماد القراءات.

  **الاعتماد الجماعي ليس رفاهية:** الاعتماد الفردي في طابور من عشرين طلبًا
  يخالف NFR-02 مباشرةً — والمشرف متطوّع بدقائق أسبوعيًّا.

  ولا حساب هنا: الساعات تُعاد من الخادم بعد الاعتماد، ولا تُشتقّ من الصفحات.
*/

const dayFormatter = new Intl.DateTimeFormat('ar-SA-u-ca-gregory-nu-latn', {
  day: 'numeric',
  month: 'long',
  timeZone: 'Asia/Riyadh',
})

const formatDay = (iso) => (iso ? dayFormatter.format(new Date(`${iso}T00:00:00Z`)) : null)

export default function ReadingQueue({ onDone }) {
  const state = useAsync(() => api.readingQueue(), [])

  return (
    <div className="taxi-in mx-auto w-full max-w-[520px] px-4 pt-6 pb-10">
      <header className="mb-5 flex items-baseline gap-3">
        <h1 className="font-display text-[26px] leading-none">طابور القراءات</h1>
        <span className="centerline" />
        <button
          type="button"
          onClick={onDone}
          className="min-h-[44px] shrink-0 px-2 text-[13px] text-muted"
        >
          رجوع
        </button>
      </header>

      <Async state={state} loadingTitle="الطابور">
        {(data) => <Queue submissions={data.submissions} onChanged={state.reload} />}
      </Async>
    </div>
  )
}

function Queue({ submissions, onChanged }) {
  const [selected, setSelected] = useState([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (submissions.length === 0) {
    return (
      <Placard title="الطابور">
        <p className="py-2 text-[14px] text-muted">لا طلبات تنتظر المراجعة.</p>
      </Placard>
    )
  }

  const toggle = (id) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]))

  async function run(action) {
    setBusy(true)
    setError('')
    try {
      await action()
      setSelected([])
      onChanged()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {/*
        صدق العدد لا مقارنته: الفحص المعماري يمنع **كل** مقارنة في مستهلكات
        العقد، لأن عتبةً مثل `hours >= 400` لا تُكتب إلا بمقارنة. والقاعدة تبقى
        صريحة بلا استثناءات — واستثناءٌ واحد اليوم يفتح البابَ لمن بعده.
      */}
      {selected.length ? (
        <button
          type="button"
          disabled={busy}
          onClick={() => run(() => api.approveReadings(selected))}
          className="min-h-[48px] w-full border border-taxi bg-taxi text-[16px] text-asphalt disabled:opacity-40"
        >
          {busy ? 'جارٍ الاعتماد…' : `اعتماد المحدَّد (${selected.length})`}
        </button>
      ) : null}

      {error && (
        <p role="alert" className="text-[13px] text-hold">
          {error}
        </p>
      )}

      {submissions.map((s) => (
        <QueueItem
          key={s.id}
          item={s}
          checked={selected.includes(s.id)}
          onToggle={() => toggle(s.id)}
          onReject={(reason) => run(() => api.rejectReading(s.id, reason))}
          busy={busy}
          formatDay={formatDay}
        />
      ))}
    </div>
  )
}

function QueueItem({ item, checked, onToggle, onReject, busy, formatDay }) {
  const [rejecting, setRejecting] = useState(false)
  const [reason, setReason] = useState('')

  return (
    <Placard title={item.student_name} aside={formatDay(item.read_on)}>
      <Row label="الكتاب" value={item.book_title} />
      <Row label="الصفحات" value={<bdi dir="ltr">{item.pages}</bdi>} />

      <div className="mt-3 flex gap-2 border-t border-concrete/35 pt-3">
        {/* أكبر هدف لأشيع فعل: التحديد للاعتماد هو الغالب، والرفض استثناء. */}
        <button
          type="button"
          onClick={onToggle}
          className={`min-h-[44px] flex-1 border text-[14px] ${
            checked ? 'border-taxi bg-taxi text-asphalt' : 'border-concrete/45 text-paint'
          }`}
        >
          {checked ? 'محدَّد ✓' : 'تحديد للاعتماد'}
        </button>
        <button
          type="button"
          onClick={() => setRejecting((v) => !v)}
          className="min-h-[44px] min-w-[88px] border border-concrete/45 px-3 text-[14px] text-muted"
        >
          رفض
        </button>
      </div>

      {rejecting && (
        <div className="mt-3">
          <label htmlFor={`reason-${item.id}`} className="mb-1.5 block text-[13px]">
            سبب الرفض — يراه الطالب
          </label>
          <input
            id={`reason-${item.id}`}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint"
          />
          <button
            type="button"
            disabled={busy || !reason.trim()}
            onClick={() => onReject(reason)}
            className="mt-2 min-h-[44px] w-full border border-hold text-[14px] text-hold disabled:opacity-40"
          >
            تأكيد الرفض
          </button>
        </div>
      )}
    </Placard>
  )
}
