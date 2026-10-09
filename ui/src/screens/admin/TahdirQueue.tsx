import { useState } from 'react'

import { api, ApiError } from '../../api'
import { fmtDecimal } from '../../api/format'
import type { QueueItem } from '../../api/types/adminQueue'
import type { StudentRef } from '../../api/types/quran'
import { useAsync } from '../../state/useAsync'
import { useSubmit } from '../../state/useSubmit'
import { Async } from '../../ui/Async'
import Button from '../../ui/Button'
import EmptyState from '../../ui/EmptyState'
import Field, { fieldClass } from '../../ui/Field'
import Placard from '../../ui/Placard'
import Prow from '../../ui/Prow'
import QueueItemCard from './QueueItemCard'
import ErrorText from '../../ui/ErrorText'

/**
 * طابور تحضير القراءة — `GET /admin/tahdir` (FR-092). **الاعتماد والرفض
 * عبر مساري القراءة العامّة القائمين حرفيًّا** — عامّان على معرّف الطلب
 * بصرف النظر عن نوعه، فلا مسارين موازيين هنا.
 */

const dayFormatter = new Intl.DateTimeFormat('ar-SA-u-ca-gregory-nu-latn', {
  day: 'numeric',
  month: 'long',
  timeZone: 'Asia/Riyadh',
})
const formatDay = (iso: string) => dayFormatter.format(new Date(`${iso}T00:00:00Z`))


function Queue({ submissions, onChanged }: { submissions: QueueItem[]; onChanged: () => void }) {
  const [selected, setSelected] = useState<number[]>([])
  const { busy, error, run } = useSubmit()

  // النجاحُ يُفرّغ التحديد ويُعيد التحميل — و`run` يُرجع `true` عنده، فالقرارُ
  // هنا لا داخل الخطّاف: شاشةٌ أخرى قد تريد إبقاءَ التحديد.
  const review = async (action: () => Promise<unknown>) => {
    if (await run(async () => void (await action()))) {
      setSelected([])
      onChanged()
    }
  }

  if (submissions.length === 0) {
    return (
      <Placard title="الطابور">
        <EmptyState>لا طلبات تنتظر المراجعة.</EmptyState>
      </Placard>
    )
  }

  const toggle = (id: number) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]))


  const idsToApprove = selected.length ? selected : submissions.map((s) => s.id)

  return (
    <div className="flex flex-col gap-3.5">
      <Button disabled={busy} onClick={() => review(() => api.admin.approveReadings(idsToApprove))} className="w-full">
        {busy ? 'جارٍ الاعتماد…' : selected.length ? `اعتماد المحدَّد (${selected.length})` : `قبول الكلّ (${submissions.length})`}
      </Button>

      {error ? <ErrorText spacing="">{error}</ErrorText> : null}

      {submissions.map((s) => (
        <QueueItemCard
          key={s.id}
          item={s}
          checked={selected.includes(s.id)}
          onToggle={() => toggle(s.id)}
          onReject={(reason) => review(() => api.admin.rejectReading(s.id, reason))}
          busy={busy}
          idPrefix="td-reason"
          formatDay={formatDay}
        />
      ))}
    </div>
  )
}

function DirectEntryForm({ students, onAdded }: { students: StudentRef[]; onAdded: () => void }) {
  const [userId, setUserId] = useState('')
  const [readOn, setReadOn] = useState('')
  const [pages, setPages] = useState('')
  const [book, setBook] = useState('')
  const [resultHours, setResultHours] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const ready = userId && readOn && pages && book.trim()

  async function submit() {
    setBusy(true)
    setError('')
    setResultHours(null)
    try {
      const result = await api.admin.adminTahdirEntry({ user_id: userId, read_on: readOn, pages, book_title: book.trim() })
      setResultHours(result.hours ? fmtDecimal(result.hours) : null)
      setReadOn('')
      setPages('')
      setBook('')
      onAdded()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Placard title="إضافة مباشرة نيابةً عن طالب">
      <Field label="الطالب" htmlFor="td_entry_student">
        <select id="td_entry_student" value={userId} onChange={(e) => setUserId(e.target.value)} className={fieldClass}>
          <option value="">اختر طالبًا</option>
          {students.map((s) => (
            <option key={s.id} value={s.id}>
              {s.full_name}
            </option>
          ))}
        </select>
      </Field>
      <Field label="التاريخ — الأحد إلى الأربعاء فقط" htmlFor="td_entry_date">
        <input id="td_entry_date" type="date" value={readOn} onChange={(e) => setReadOn(e.target.value)} className={fieldClass} />
      </Field>
      <Field label="الصفحات" htmlFor="td_entry_pages">
        <input id="td_entry_pages" inputMode="numeric" value={pages} onChange={(e) => setPages(e.target.value)} className={fieldClass} />
      </Field>
      <Field label="الكتاب" htmlFor="td_entry_book">
        <input id="td_entry_book" value={book} onChange={(e) => setBook(e.target.value)} className={fieldClass} />
      </Field>

      {error ? <ErrorText>{error}</ErrorText> : null}
      {resultHours ? <Prow label="أُضيف" value={<bdi dir="ltr">{resultHours}</bdi>} tone="accent" /> : null}

      <Button disabled={busy || !ready} onClick={submit} className="mt-2 w-full">
        {busy ? 'جارٍ الإضافة…' : 'إضافة'}
      </Button>
    </Placard>
  )
}

export default function TahdirQueue() {
  const queueState = useAsync(() => api.admin.tahdirQueue(), [])
  const studentsState = useAsync(() => api.admin.quranStudents(), [])

  return (
    <div className="flex flex-col gap-3.5">
      <Async state={queueState} loadingTitle="طابور تحضير القراءة">
        {(data) => <Queue submissions={data.submissions} onChanged={queueState.reload} />}
      </Async>
      <Async state={studentsState} loadingTitle="طابور تحضير القراءة">
        {(data) => <DirectEntryForm students={data.students} onAdded={queueState.reload} />}
      </Async>
    </div>
  )
}
