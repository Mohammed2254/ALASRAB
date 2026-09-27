import { useState } from 'react'

import { api, ApiError } from '../../api'
import type { QueueItem } from '../../api/types/adminQueue'
import { useAsync } from '../../state/useAsync'
import { Async } from '../../ui/Async'
import Button from '../../ui/Button'
import EmptyState from '../../ui/EmptyState'
import Placard from '../../ui/Placard'
import Prow from '../../ui/Prow'

/**
 * طابور اعتماد القراءات — `GET/POST /admin/readings*` (FR-022..024).
 * **الاعتماد الجماعي ليس رفاهية**: الاعتماد الفردي في طابور من عشرين طلبًا
 * يخالف NFR-02. ولا حساب هنا — الساعات تعود من الخادم بعد الاعتماد.
 */

const dayFormatter = new Intl.DateTimeFormat('ar-SA-u-ca-gregory-nu-latn', {
  day: 'numeric',
  month: 'long',
  timeZone: 'Asia/Riyadh',
})
const formatDay = (iso: string) => dayFormatter.format(new Date(`${iso}T00:00:00Z`))

function QueueItemCard({
  item,
  checked,
  onToggle,
  onReject,
  busy,
}: {
  item: QueueItem
  checked: boolean
  onToggle: () => void
  onReject: (reason: string) => void
  busy: boolean
}) {
  const [rejecting, setRejecting] = useState(false)
  const [reason, setReason] = useState('')

  return (
    <Placard title={item.student_name} aside={formatDay(item.read_on)}>
      <Prow label="الكتاب" value={item.book_title} />
      <Prow label="الصفحات" value={<bdi dir="ltr">{item.pages}</bdi>} />

      <div className="mt-3 flex gap-2 border-t border-(--color-border) pt-3">
        <button
          type="button"
          onClick={onToggle}
          className={`min-h-[44px] flex-1 rounded-(--radius-sm) border text-[14px] ${
            checked
              ? 'border-(--color-accent) bg-(--color-accent) text-(--color-on-accent)'
              : 'border-(--color-border-strong) text-(--color-text)'
          }`}
        >
          {checked ? 'محدَّد ✓' : 'تحديد للاعتماد'}
        </button>
        <button
          type="button"
          onClick={() => setRejecting((v) => !v)}
          className="min-h-[44px] min-w-[88px] rounded-(--radius-sm) border border-(--color-border-strong) px-3 text-[14px] text-(--color-text-dim)"
        >
          رفض
        </button>
      </div>

      {rejecting ? (
        <div className="mt-3">
          <label htmlFor={`reason-${item.id}`} className="mb-1.5 block text-[13px] text-(--color-text-dim)">
            سبب الرفض — يراه الطالب
          </label>
          <input
            id={`reason-${item.id}`}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="min-h-[48px] w-full rounded-(--radius-sm) border border-(--color-border-strong) bg-(--color-bg-2) px-3 text-[16px] text-(--color-text)"
          />
          <Button
            variant="danger"
            disabled={busy || !reason.trim()}
            onClick={() => onReject(reason)}
            className="mt-2 w-full"
          >
            تأكيد الرفض
          </Button>
        </div>
      ) : null}
    </Placard>
  )
}

function Queue({ submissions, onChanged }: { submissions: QueueItem[]; onChanged: () => void }) {
  const [selected, setSelected] = useState<number[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (submissions.length === 0) {
    return (
      <Placard title="الطابور">
        <EmptyState>لا طلبات تنتظر المراجعة.</EmptyState>
      </Placard>
    )
  }

  const toggle = (id: number) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]))

  async function run(action: () => Promise<unknown>) {
    setBusy(true)
    setError('')
    try {
      await action()
      setSelected([])
      onChanged()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-3.5">
      {selected.length ? (
        <Button disabled={busy} onClick={() => run(() => api.admin.approveReadings(selected))} className="w-full">
          {busy ? 'جارٍ الاعتماد…' : `اعتماد المحدَّد (${selected.length})`}
        </Button>
      ) : null}

      {error ? (
        <p role="alert" className="text-[13px] text-(--color-red-text)">
          {error}
        </p>
      ) : null}

      {submissions.map((s) => (
        <QueueItemCard
          key={s.id}
          item={s}
          checked={selected.includes(s.id)}
          onToggle={() => toggle(s.id)}
          onReject={(reason) => run(() => api.admin.rejectReading(s.id, reason))}
          busy={busy}
        />
      ))}
    </div>
  )
}

export default function ReadingQueue() {
  const state = useAsync(() => api.admin.readingQueue(), [])

  return (
    <div className="flex flex-col gap-3.5">
      <Async state={state} loadingTitle="الطابور">
        {(data) => <Queue submissions={data.submissions} onChanged={state.reload} />}
      </Async>
    </div>
  )
}
