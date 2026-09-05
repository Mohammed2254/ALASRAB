import { useState } from 'react'

import Placard from '../../components/Placard'
import { Async } from '../../components/States'
import { api } from '../../lib/api'
import { useAsync } from '../../state/useAsync'

/*
  اختيار طيار الأسبوع — و-٩د · FR-062 · م-٦.

  **مرشّحو الاختيار من التقرير الدوري** (`top_movers`) لا من قائمة طلاب
  عامّة جديدة — «من تحرّك هذا الأسبوع» هو نفسه معنى «طيار الأسبوع»، ولا
  حاجة إلى مسار جديد لعرض كل الطلاب لأجل هذا وحده.

  **اختيار واحد لكل أسبوع بلا تراجع** (ث-٩): إن كان مختارًا لهذا الأسبوع لا
  يُعرض نموذج جديد أصلًا — الخادم يرفضه بـ٤٠٩ على أي حال، لكن إخفاء النموذج
  يمنع المحاولة العبثية بدل ترك الخادم يرفضها.
*/

export default function AdminWeekPilot({ onDone }) {
  const state = useAsync(
    () => Promise.all([api.weekPilot(), api.report(7)]).then(([week, report]) => ({ week, report })),
    [],
  )

  return (
    <div className="taxi-in mx-auto w-full max-w-[520px] px-4 pt-6 pb-10">
      <header className="mb-5 flex items-baseline gap-3">
        <h1 className="font-display text-[26px] leading-none">اختيار طيار الأسبوع</h1>
        <span className="centerline" />
        <button
          type="button"
          onClick={onDone}
          className="min-h-[44px] shrink-0 px-2 text-[13px] text-muted"
        >
          رجوع
        </button>
      </header>

      <Async state={state} loadingTitle="طيار الأسبوع">
        {({ week, report }) =>
          week.pilot ? (
            <Placard title={week.pilot.full_name} aside="مختار لهذا الأسبوع">
              <p className="py-2 text-[14px] text-paint">{week.pilot.reason}</p>
            </Placard>
          ) : (
            <ChooseForm candidates={report.top_movers} onChosen={state.reload} />
          )
        }
      </Async>
    </div>
  )
}

function ChooseForm({ candidates, onChosen }) {
  const [userId, setUserId] = useState(null)
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function onSubmit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api.chooseWeekPilot(userId, reason.trim())
      onChosen()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (!candidates.length) {
    return (
      <Placard title="طيار الأسبوع">
        <p className="py-2 text-[14px] text-muted">لا متحرّكون هذا الأسبوع لاختيار أحدهم بعد.</p>
      </Placard>
    )
  }

  return (
    <Placard title="اختر من متحرّكي هذا الأسبوع">
      <form onSubmit={onSubmit} className="flex flex-col gap-3">
        <div className="flex flex-col gap-2">
          {candidates.map((c) => (
            <button
              key={c.user_id}
              type="button"
              onClick={() => setUserId(c.user_id)}
              className={`flex min-h-[44px] w-full items-center justify-between gap-3 border px-3 text-[14px] ${userId === c.user_id ? 'border-taxi text-taxi' : 'border-concrete/45 text-paint'}`}
            >
              <span>{c.full_name}</span>
              <bdi dir="ltr">{c.hours}</bdi>
            </button>
          ))}
        </div>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={4}
          placeholder="السبب — القيمة كلّها هنا لا في الاسم"
          className="w-full border border-concrete/45 bg-transparent p-3 text-[14px] text-paint"
        />
        {error && <p className="text-[13px] text-hold">{error}</p>}
        <button
          type="submit"
          disabled={busy || !userId || !reason.trim()}
          className="min-h-[44px] border border-taxi text-[14px] text-taxi disabled:opacity-50"
        >
          اختيار
        </button>
      </form>
    </Placard>
  )
}
