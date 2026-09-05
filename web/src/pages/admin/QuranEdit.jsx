import { useState } from 'react'

import Placard, { Row } from '../../components/Placard'
import { Async } from '../../components/States'
import { api } from '../../lib/api'
import { useAsync } from '../../state/useAsync'

/*
  التصحيح والتعديل القرآني — و-٦ · FR-035 · FR-036 · FR-037 · FR-080.

  **راصد قاعدة، والتعديل اليدوي استثناء** (`ADR-004`): كل تصحيح وكل إضافة
  بسبب مكتوب إلزاميًّا، ويظهران في سجلّ التغييرات وفي بطاقة الطالب بلا شاشة
  إضافية — `point_events`/`audit_log` القائمان يستوعبانهما.

  **الساعات هنا نصٌّ يأتي من الخادم فقط** — `delta` يُعرض كما وصل، ولا حساب
  أو مقارنة عليه (AGENTS ٥).
*/

export default function QuranEdit({ onDone }) {
  const state = useAsync(() => api.quranStudents(), [])

  return (
    <div className="taxi-in mx-auto w-full max-w-[520px] px-4 pt-6 pb-10">
      <header className="mb-5 flex items-baseline gap-3">
        <h1 className="font-display text-[26px] leading-none">التصحيح والتعديل القرآني</h1>
        <span className="centerline" />
        <button
          type="button"
          onClick={onDone}
          className="min-h-[44px] shrink-0 px-2 text-[13px] text-muted"
        >
          رجوع
        </button>
      </header>

      <Async state={state} loadingTitle="التصحيح والتعديل القرآني">
        {(data) => <Body students={data.students} />}
      </Async>
    </div>
  )
}

function Body({ students }) {
  const [userId, setUserId] = useState('')

  return (
    <div className="flex flex-col gap-4">
      <Placard title="اختر طالبًا">
        <label htmlFor="qe_student" className="mb-1.5 block text-[13px]">
          الطالب
        </label>
        <select
          id="qe_student"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          className="min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint"
        >
          <option value="">اختر طالبًا</option>
          {students.map((s) => (
            <option key={s.id} value={s.id}>
              {s.full_name}
            </option>
          ))}
        </select>
      </Placard>

      {userId && <StudentEvents userId={userId} />}
      <AddEntryForm students={students} defaultUserId={userId} />
    </div>
  )
}

function StudentEvents({ userId }) {
  const state = useAsync(() => api.quranEvents(userId), [userId])

  return (
    <Async state={state} loadingTitle="أحداث الطالب">
      {(data) =>
        data.events.length === 0 ? (
          <Placard title="أحداث الطالب">
            <p className="py-2 text-[14px] text-muted">لا أحداث لهذا الطالب بعد.</p>
          </Placard>
        ) : (
          <Placard title="أحداث الطالب — الأحدث أوّلًا">
            {data.events.map((e) => (
              <EventRow key={e.id} event={e} onReversed={state.reload} />
            ))}
          </Placard>
        )
      }
    </Async>
  )
}

function EventRow({ event, onReversed }) {
  const [correcting, setCorrecting] = useState(false)
  const [reason, setReason] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function confirm() {
    setBusy(true)
    setError('')
    try {
      await api.reverseEvent(event.id, reason)
      setReason('')
      setCorrecting(false)
      onReversed()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mb-2 border-b border-concrete/35 pb-2 last:border-0">
      <Row label={event.kind} value={<bdi dir="ltr">{event.delta}</bdi>} />
      {event.reason && <p className="text-[12px] text-muted">{event.reason}</p>}

      {correcting ? (
        <div className="mt-2">
          <label htmlFor={`qe_reason_${event.id}`} className="mb-1.5 block text-[13px]">
            سبب التصحيح — إلزاميّ
          </label>
          <input
            id={`qe_reason_${event.id}`}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint"
          />
          {error && (
            <p role="alert" className="mt-1 text-[13px] text-hold">
              {error}
            </p>
          )}
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              disabled={busy || !reason.trim()}
              onClick={confirm}
              className="min-h-[44px] flex-1 border border-hold text-[14px] text-hold disabled:opacity-40"
            >
              تأكيد التصحيح
            </button>
            <button
              type="button"
              onClick={() => setCorrecting(false)}
              className="min-h-[44px] min-w-[80px] border border-concrete/45 text-[14px] text-muted"
            >
              إلغاء
            </button>
          </div>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setCorrecting(true)}
          className="mt-1 min-h-[44px] w-full border border-concrete/45 text-[13px] text-muted"
        >
          تصحيح
        </button>
      )}
    </div>
  )
}

function AddEntryForm({ students, defaultUserId }) {
  const [userId, setUserId] = useState(defaultUserId)
  const [activityType, setActivityType] = useState('')
  const [quantity, setQuantity] = useState('')
  const [mastery, setMastery] = useState('')
  const [occurredOn, setOccurredOn] = useState('')
  const [reason, setReason] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const effectiveUserId = userId || defaultUserId
  const ready =
    effectiveUserId && activityType.trim() && quantity.trim() && occurredOn && reason.trim()

  async function submit() {
    setBusy(true)
    setError('')
    setResult(null)
    try {
      const body = {
        user_id: Number(effectiveUserId),
        occurred_on: occurredOn,
        activity_type: activityType.trim(),
        quantity,
        reason: reason.trim(),
      }
      if (mastery.trim()) body.mastery = mastery.trim()
      setResult(await api.quranEntry(body))
      setActivityType('')
      setQuantity('')
      setMastery('')
      setOccurredOn('')
      setReason('')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Placard title="إضافة سجلّ ناقص يدويًّا">
      <label htmlFor="qe_add_student" className="mb-1.5 block text-[13px]">
        الطالب
      </label>
      <select
        id="qe_add_student"
        value={effectiveUserId}
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

      <label htmlFor="qe_activity" className="mb-1.5 block text-[13px]">
        نوع النشاط
      </label>
      <input
        id="qe_activity"
        value={activityType}
        onChange={(e) => setActivityType(e.target.value)}
        placeholder="memorize · review · …"
        className="mb-3 min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint"
      />

      <label htmlFor="qe_quantity" className="mb-1.5 block text-[13px]">
        الكمّية
      </label>
      <input
        id="qe_quantity"
        inputMode="decimal"
        value={quantity}
        onChange={(e) => setQuantity(e.target.value)}
        className="mb-3 min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint"
      />

      <label htmlFor="qe_mastery" className="mb-1.5 block text-[13px]">
        التقدير — اختياريّ
      </label>
      <input
        id="qe_mastery"
        value={mastery}
        onChange={(e) => setMastery(e.target.value)}
        placeholder="mastered · accepted · repeat"
        className="mb-3 min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint"
      />

      <label htmlFor="qe_date" className="mb-1.5 block text-[13px]">
        تاريخ الوقوع
      </label>
      <input
        id="qe_date"
        type="date"
        value={occurredOn}
        onChange={(e) => setOccurredOn(e.target.value)}
        className="mb-3 min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint"
      />

      <label htmlFor="qe_add_reason" className="mb-1.5 block text-[13px]">
        السبب — إلزاميّ
      </label>
      <textarea
        id="qe_add_reason"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        rows={4}
        placeholder="غاب عن تصدير راصد هذا الأسبوع"
        className="mb-3 w-full border border-concrete/45 bg-taxiway p-3 text-[14px] text-paint"
      />

      {error && (
        <p role="alert" className="mb-3 text-[13px] text-hold">
          {error}
        </p>
      )}
      {result && (
        <Row label="أُضيف" value={<bdi dir="ltr">{result.delta}</bdi>} tone="taxi" />
      )}

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
