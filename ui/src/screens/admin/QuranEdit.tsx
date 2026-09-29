import { useState } from 'react'

import { api, ApiError } from '../../api'
import { fmtDecimal } from '../../api/format'
import type { StudentRef } from '../../api/types/quran'
import { useAsync } from '../../state/useAsync'
import { Async } from '../../ui/Async'
import Button from '../../ui/Button'
import EmptyState from '../../ui/EmptyState'
import Field from '../../ui/Field'
import Placard from '../../ui/Placard'
import EventRow from './QuranEventRow'
import Prow from '../../ui/Prow'

/**
 * التصحيح والتعديل القرآني — `GET /admin/quran/{students,events}` ·
 * `POST /admin/events/{id}/reverse` · `POST /admin/quran/entry`
 * (FR-035..037 · FR-080). **راصد قاعدة، والتعديل اليدوي استثناء** (ADR-004):
 * كل تصحيح وكل إضافة بسبب مكتوب إلزاميًّا — حدثٌ معاكس، لا `UPDATE`/`DELETE`
 * أبدًا. الساعات نصٌّ يأتي من الخادم فقط — تُعرض كما وصلت (`AGENTS.md` ٥).
 */
const fieldClass = 'min-h-[48px] w-full rounded-(--radius-sm) border border-(--color-border-strong) bg-(--color-bg-2) px-3 text-[16px] text-(--color-text)'

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
              <EventRow key={e.id} event={e} onChanged={state.reload} />
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
