import { useState } from 'react'

import { api, ApiError } from '../../api'
import { fmtDecimal } from '../../api/format'
import type { Mover } from '../../api/types/report'
import { useAsync } from '../../state/useAsync'
import { Async } from '../../ui/Async'
import EmptyState from '../../ui/EmptyState'
import Placard from '../../ui/Placard'

/**
 * اختيار طيار الأسبوع — `POST /admin/week/pilot` (FR-062 · م-٦).
 * **مرشّحو الاختيار من التقرير الدوري** (`top_movers`) لا قائمة طلاب عامّة
 * جديدة — «من تحرّك هذا الأسبوع» هو نفسه معنى «طيار الأسبوع». **اختيارٌ
 * واحد لكل أسبوع بلا تراجع** (ث-٩): إن كان مختارًا لا يُعرض النموذج أصلًا.
 */
function ChooseForm({ candidates, onChosen }: { candidates: Mover[]; onChosen: () => void }) {
  const [userId, setUserId] = useState<number | null>(null)
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit() {
    if (userId === null) return
    setBusy(true)
    setError('')
    try {
      await api.admin.chooseWeekPilot({ user_id: userId, reason: reason.trim() })
      onChosen()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
    } finally {
      setBusy(false)
    }
  }

  if (!candidates.length) {
    return (
      <Placard title="طيار الأسبوع">
        <EmptyState>لا متحرّكون هذا الأسبوع لاختيار أحدهم بعد.</EmptyState>
      </Placard>
    )
  }

  return (
    <Placard title="المرشّحون">
      <div className="flex flex-col gap-3.5">
        <div className="flex flex-col gap-2">
          {candidates.map((c) => (
            <button
              key={c.user_id}
              type="button"
              onClick={() => setUserId(c.user_id)}
              className={`flex min-h-[44px] w-full items-center justify-between gap-3 rounded-(--radius-sm) border px-3 text-[14px] ${
                userId === c.user_id ? 'border-(--color-accent) text-(--color-accent)' : 'border-(--color-border-strong) text-(--color-text)'
              }`}
            >
              <span>{c.full_name}</span>
              <bdi dir="ltr">{fmtDecimal(c.hours)}</bdi>
            </button>
          ))}
        </div>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={4}
          placeholder="السبب — القيمة كلّها هنا لا في الاسم"
          className="w-full rounded-(--radius-sm) border border-(--color-border-strong) bg-(--color-bg-2) p-3 text-[16px] text-(--color-text)"
        />
        {error ? (
          <p role="alert" className="text-[13px] text-(--color-red-text)">
            {error}
          </p>
        ) : null}
        <button
          type="button"
          disabled={busy || userId === null || !reason.trim()}
          onClick={submit}
          className="min-h-[44px] rounded-(--radius-sm) border border-(--color-accent) text-[14px] text-(--color-accent) disabled:opacity-50"
        >
          اختيار
        </button>
      </div>
    </Placard>
  )
}

export default function AdminWeekPilot() {
  const state = useAsync(
    () => Promise.all([api.engagement.weekPilot(), api.admin.report(7)]).then(([week, report]) => ({ week, report })),
    []
  )

  return (
    <div className="flex flex-col gap-3.5">
      <Async state={state} loadingTitle="طيار الأسبوع">
        {({ week, report }) =>
          week.pilot ? (
            <Placard title={week.pilot.full_name} aside="مختار لهذا الأسبوع">
              <p className="py-2 text-[14px] text-(--color-text)">{week.pilot.reason}</p>
            </Placard>
          ) : (
            <ChooseForm candidates={report.top_movers} onChosen={state.reload} />
          )
        }
      </Async>
    </div>
  )
}
