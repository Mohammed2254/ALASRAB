import { useState } from 'react'

import Placard, { Row } from '../../components/Placard'
import { Async } from '../../components/States'
import { api } from '../../lib/api'
import { useAsync } from '../../state/useAsync'

/*
  طابور تحضير القراءة — و-١١ · FR-092.

  **الاعتماد والرفض عبر مساري القراءة العامّة القائمين حرفيًّا** —
  `api.approveReadings`/`api.rejectReading` — عامّان على معرّف الطلب بصرف
  النظر عن نوعه، فلا حاجة لمسارين موازيين هنا.
*/

const dayFormatter = new Intl.DateTimeFormat('ar-SA-u-ca-gregory-nu-latn', {
  day: 'numeric',
  month: 'long',
  timeZone: 'Asia/Riyadh',
})

const formatDay = (iso) => (iso ? dayFormatter.format(new Date(`${iso}T00:00:00Z`)) : null)

export default function TahdirQueue({ onDone }) {
  const queueState = useAsync(() => api.tahdirQueue(), [])
  const studentsState = useAsync(() => api.quranStudents(), [])

  return (
    <div className="taxi-in mx-auto w-full max-w-[520px] px-4 pt-6 pb-10">
      <header className="mb-5 flex items-baseline gap-3">
        <h1 className="font-display text-[26px] leading-none">طابور تحضير القراءة</h1>
        <span className="centerline" />
        <button
          type="button"
          onClick={onDone}
          className="min-h-[44px] shrink-0 px-2 text-[13px] text-muted"
        >
          رجوع
        </button>
      </header>

      <div className="flex flex-col gap-4">
        <Async state={queueState} loadingTitle="طابور تحضير القراءة">
          {(data) => <Queue submissions={data.submissions} onChanged={queueState.reload} />}
        </Async>

        <Async state={studentsState} loadingTitle="طابور تحضير القراءة">
          {(data) => <DirectEntryForm students={data.students} onAdded={queueState.reload} />}
        </Async>
      </div>
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
      {selected.length ? (
        <button
          type="button"
          disabled={busy}
          onClick={() => run(() => api.approveReadings(selected))}
          className="min-h-[48px] w-full border border-taxi bg-taxi text-[16px] text-asphalt disabled:opacity-40"
        >
          {busy ? 'جارٍ الاعتماد…' : `اعتماد المحدَّد (${selected.length})`}
        </button>
      ) : (
        <button
          type="button"
          disabled={busy}
          onClick={() => run(() => api.approveReadings(submissions.map((s) => s.id)))}
          className="min-h-[48px] w-full border border-taxi bg-taxi text-[16px] text-asphalt disabled:opacity-40"
        >
          {busy ? 'جارٍ الاعتماد…' : `اعتماد الكلّ (${submissions.length})`}
        </button>
      )}

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
        />
      ))}
    </div>
  )
}

function QueueItem({ item, checked, onToggle, onReject, busy }) {
  const [rejecting, setRejecting] = useState(false)
  const [reason, setReason] = useState('')

  return (
    <Placard title={item.student_name} aside={formatDay(item.read_on)}>
      <Row label="الكتاب" value={item.book_title} />
      <Row label="الصفحات" value={<bdi dir="ltr">{item.pages}</bdi>} />

      <div className="mt-3 flex gap-2 border-t border-concrete/35 pt-3">
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
          <label htmlFor={`td-reason-${item.id}`} className="mb-1.5 block text-[13px]">
            سبب الرفض — يراه الطالب
          </label>
          <input
            id={`td-reason-${item.id}`}
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

function DirectEntryForm({ students, onAdded }) {
  const [userId, setUserId] = useState('')
  const [readOn, setReadOn] = useState('')
  const [pages, setPages] = useState('')
  const [book, setBook] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const ready = userId && readOn && pages && book.trim()

  async function submit() {
    setBusy(true)
    setError('')
    setResult(null)
    try {
      setResult(
        await api.adminTahdirEntry({
          user_id: Number(userId),
          read_on: readOn,
          pages: Number(pages),
          book_title: book.trim(),
        }),
      )
      setReadOn('')
      setPages('')
      setBook('')
      onAdded()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Placard title="إضافة مباشرة نيابةً عن طالب">
      <label htmlFor="td_entry_student" className="mb-1.5 block text-[13px]">
        الطالب
      </label>
      <select
        id="td_entry_student"
        value={userId}
        onChange={(e) => setUserId(e.target.value)}
        className="mb-3 min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint"
      >
        <option value="">اختر طالبًا</option>
        {students.map((s) => (
          <option key={s.id} value={s.id}>
            {s.full_name}
          </option>
        ))}
      </select>

      <label htmlFor="td_entry_date" className="mb-1.5 block text-[13px]">
        التاريخ — الأحد إلى الأربعاء فقط
      </label>
      <input
        id="td_entry_date"
        type="date"
        value={readOn}
        onChange={(e) => setReadOn(e.target.value)}
        className="mb-3 min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint"
      />

      <label htmlFor="td_entry_pages" className="mb-1.5 block text-[13px]">
        الصفحات
      </label>
      <input
        id="td_entry_pages"
        inputMode="numeric"
        value={pages}
        onChange={(e) => setPages(e.target.value)}
        className="mb-3 min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint"
      />

      <label htmlFor="td_entry_book" className="mb-1.5 block text-[13px]">
        الكتاب
      </label>
      <input
        id="td_entry_book"
        value={book}
        onChange={(e) => setBook(e.target.value)}
        className="mb-3 min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint"
      />

      {error && (
        <p role="alert" className="mb-3 text-[13px] text-hold">
          {error}
        </p>
      )}
      {result && <Row label="أُضيف" value={<bdi dir="ltr">{result.hours}</bdi>} tone="taxi" />}

      <button
        type="button"
        disabled={busy || !ready}
        onClick={submit}
        className="mt-2 min-h-[48px] w-full border border-taxi bg-taxi text-[16px] text-asphalt disabled:opacity-40"
      >
        {busy ? 'جارٍ الإضافة…' : 'إضافة'}
      </button>
    </Placard>
  )
}
