import { useState } from 'react'

import { api, ApiError } from '../../api'
import { fmtDecimal } from '../../api/format'
import type { QuranEventRow, StudentRef } from '../../api/types/quran'
import { useAsync } from '../../state/useAsync'
import { Async } from '../../ui/Async'
import Button from '../../ui/Button'
import EmptyState from '../../ui/EmptyState'
import Field from '../../ui/Field'
import Placard from '../../ui/Placard'
import Prow from '../../ui/Prow'

/**
 * التصحيح والتعديل القرآني — `GET /admin/quran/{students,events}` ·
 * `POST /admin/events/{id}/reverse` · `POST /admin/quran/entry`
 * (FR-035..037 · FR-080). **راصد قاعدة، والتعديل اليدوي استثناء** (ADR-004):
 * كل تصحيح وكل إضافة بسبب مكتوب إلزاميًّا — حدثٌ معاكس، لا `UPDATE`/`DELETE`
 * أبدًا. الساعات نصٌّ يأتي من الخادم فقط — تُعرض كما وصلت (`AGENTS.md` ٥).
 */
const fieldClass = 'min-h-[48px] w-full rounded-(--radius-sm) border border-(--color-border-strong) bg-(--color-bg-2) px-3 text-[16px] text-(--color-text)'

function EventRow({ event, onReversed }: { event: QuranEventRow; onReversed: () => void }) {
  const [correcting, setCorrecting] = useState(false)
  const [reason, setReason] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function confirm() {
    setBusy(true)
    setError('')
    try {
      await api.admin.reverseEvent(event.id, reason)
      setReason('')
      setCorrecting(false)
      onReversed()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mb-2 border-b border-(--color-border) pb-2 last:border-none">
      <Prow label={event.kind} value={<bdi dir="ltr">{fmtDecimal(event.delta)}</bdi>} />
      {event.reason ? <p className="text-[12px] text-(--color-text-dim)">{event.reason}</p> : null}

      {correcting ? (
        <div className="mt-2">
          <label htmlFor={`qe_reason_${event.id}`} className="mb-1.5 block text-[13px] text-(--color-text-dim)">
            سبب التصحيح — إلزاميّ
          </label>
          <input id={`qe_reason_${event.id}`} value={reason} onChange={(e) => setReason(e.target.value)} className={fieldClass} />
          {error ? (
            <p role="alert" className="mt-1 text-[13px] text-(--color-red-text)">
              {error}
            </p>
          ) : null}
          <div className="mt-2 flex gap-2">
            <Button variant="danger" disabled={busy || !reason.trim()} onClick={confirm} className="flex-1">
              تأكيد التصحيح
            </Button>
            <Button variant="outline" onClick={() => setCorrecting(false)} className="min-w-[80px]">
              إلغاء
            </Button>
          </div>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setCorrecting(true)}
          className="mt-1 min-h-[44px] w-full rounded-(--radius-sm) border border-(--color-border-strong) text-[13px] text-(--color-text-dim)"
        >
          تصحيح
        </button>
      )}
    </div>
  )
}

function StudentEvents({ userId }: { userId: string }) {
  const state = useAsync(() => api.admin.quranEvents(userId), [userId])

  return (
    <Async state={state} loadingTitle="أحداث الطالب">
      {(data) =>
        data.events.length === 0 ? (
          <Placard title="أحداث الطالب">
            <EmptyState>لا أحداث لهذا الطالب بعد.</EmptyState>
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

function AddEntryForm({ students, defaultUserId }: { students: StudentRef[]; defaultUserId: string }) {
  const [userId, setUserId] = useState(defaultUserId)
  const [activityType, setActivityType] = useState('')
  const [quantity, setQuantity] = useState('')
  const [mastery, setMastery] = useState('')
  const [occurredOn, setOccurredOn] = useState('')
  const [reason, setReason] = useState('')
  const [resultDelta, setResultDelta] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const effectiveUserId = userId || defaultUserId
  const ready = effectiveUserId && activityType.trim() && quantity.trim() && occurredOn && reason.trim()

  async function submit() {
    setBusy(true)
    setError('')
    setResultDelta(null)
    try {
      const result = await api.admin.quranEntry({
        user_id: effectiveUserId,
        occurred_on: occurredOn,
        activity_type: activityType.trim(),
        quantity,
        mastery: mastery.trim() || null,
        reason: reason.trim(),
      })
      setResultDelta(fmtDecimal(result.delta))
      setActivityType('')
      setQuantity('')
      setMastery('')
      setOccurredOn('')
      setReason('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Placard title="إضافة سجلّ جديد">
      <Field label="الطالب" htmlFor="qe_add_student">
        <select id="qe_add_student" value={effectiveUserId} onChange={(e) => setUserId(e.target.value)} className={fieldClass}>
          <option value="">اختر طالبًا</option>
          {students.map((s) => (
            <option key={s.id} value={s.id}>
              {s.full_name}
            </option>
          ))}
        </select>
      </Field>
      <Field label="نوع النشاط" htmlFor="qe_activity">
        <input id="qe_activity" value={activityType} onChange={(e) => setActivityType(e.target.value)} placeholder="memorize · review · …" className={fieldClass} />
      </Field>
      <Field label="الكمّية" htmlFor="qe_quantity">
        <input id="qe_quantity" inputMode="decimal" value={quantity} onChange={(e) => setQuantity(e.target.value)} className={fieldClass} />
      </Field>
      <Field label="التقدير — اختياريّ" htmlFor="qe_mastery">
        <input id="qe_mastery" value={mastery} onChange={(e) => setMastery(e.target.value)} placeholder="mastered · accepted · repeat" className={fieldClass} />
      </Field>
      <Field label="تاريخ الوقوع" htmlFor="qe_date">
        <input id="qe_date" type="date" value={occurredOn} onChange={(e) => setOccurredOn(e.target.value)} className={fieldClass} />
      </Field>
      <Field label="السبب — إلزاميّ" htmlFor="qe_add_reason">
        <textarea
          id="qe_add_reason"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={4}
          placeholder="غاب عن تصدير راصد هذا الأسبوع"
          className="w-full rounded-(--radius-sm) border border-(--color-border-strong) bg-(--color-bg-2) p-3 text-[14px] text-(--color-text)"
        />
      </Field>

      {error ? (
        <p role="alert" className="mb-3 text-[13px] text-(--color-red-text)">
          {error}
        </p>
      ) : null}
      {resultDelta ? <Prow label="أُضيف" value={<bdi dir="ltr">{resultDelta}</bdi>} tone="accent" /> : null}

      <Button disabled={busy || !ready} onClick={submit} className="mt-2 w-full">
        {busy ? 'جارٍ الإضافة…' : 'إضافة'}
      </Button>
    </Placard>
  )
}

function Body({ students }: { students: StudentRef[] }) {
  const [userId, setUserId] = useState('')

  return (
    <div className="flex flex-col gap-3.5">
      <Placard title="بحث عن طالب">
        <Field label="الطالب" htmlFor="qe_student">
          <select id="qe_student" value={userId} onChange={(e) => setUserId(e.target.value)} className={fieldClass}>
            <option value="">اختر طالبًا</option>
            {students.map((s) => (
              <option key={s.id} value={s.id}>
                {s.full_name}
              </option>
            ))}
          </select>
        </Field>
      </Placard>

      {userId ? <StudentEvents userId={userId} /> : null}
      <AddEntryForm students={students} defaultUserId={userId} />
    </div>
  )
}

export default function QuranEdit() {
  const state = useAsync(() => api.admin.quranStudents(), [])

  return (
    <div className="flex flex-col gap-3.5">
      <Async state={state} loadingTitle="التصحيح والتعديل القرآني">
        {(data) => <Body students={data.students} />}
      </Async>
    </div>
  )
}
