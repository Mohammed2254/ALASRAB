import { useState } from 'react'

import Placard, { Row } from '../../components/Placard'
import { Async } from '../../components/States'
import { api } from '../../lib/api'
import { useAsync } from '../../state/useAsync'

/*
  الحضور اليدويّ — و-٩هـ · FR-041/FR-042 (احتياطيّ).

  **الجميع حاضر افتراضًا** (FR-041 الحرفي) — الشاشة تفتح وكل زرّ بلون
  الحضور، والمشرف ينقر الغائب وحده فيتحوّل لونه. لا حساب هنا: `hours_each`
  يصل جاهزًا من الخادم (وزن الحضور الفعليّ، لا رقم في الكود).
*/

export default function Attendance({ onDone }) {
  const state = useAsync(() => api.attendance(), [])

  return (
    <div className="taxi-in mx-auto w-full max-w-[520px] px-4 pt-6 pb-10">
      <header className="mb-5 flex items-baseline gap-3">
        <h1 className="font-display text-[26px] leading-none">الحضور</h1>
        <span className="centerline" />
        <button
          type="button"
          onClick={onDone}
          className="min-h-[44px] shrink-0 px-2 text-[13px] text-muted"
        >
          رجوع
        </button>
      </header>

      <Async state={state} loadingTitle="الحضور">
        {(data) =>
          data.already_recorded ? (
            <Recorded data={data} onChanged={state.reload} />
          ) : (
            <RollCall pilots={data.pilots} onRecorded={state.reload} />
          )
        }
      </Async>
    </div>
  )
}

function RollCall({ pilots, onRecorded }) {
  const [absentIds, setAbsentIds] = useState([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  function toggle(id) {
    setAbsentIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  async function submit() {
    setBusy(true)
    setError('')
    try {
      await api.recordAttendance(absentIds)
      onRecorded()
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <Placard title="حضور هذا الأسبوع" aside={`${pilots.length} طيّارًا`}>
      <div className="flex flex-col gap-2">
        {pilots.map((p) => {
          const absent = absentIds.includes(p.user_id)
          return (
            <button
              key={p.user_id}
              type="button"
              onClick={() => toggle(p.user_id)}
              className={`flex min-h-[44px] w-full items-center justify-between gap-3 border px-3 text-[14px] ${absent ? 'border-hold text-hold' : 'border-taxi text-taxi'}`}
            >
              <span>{p.full_name}</span>
              <span>{absent ? 'غائب' : 'حاضر'}</span>
            </button>
          )
        })}
      </div>
      {error && <p className="mt-3 text-[13px] text-hold">{error}</p>}
      <button
        type="button"
        onClick={submit}
        disabled={busy}
        className="mt-4 min-h-[44px] w-full border border-taxi text-[14px] text-taxi disabled:opacity-50"
      >
        حفظ الحضور
      </button>
    </Placard>
  )
}

function Recorded({ data, onChanged }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const canUndo = Boolean(data.undo_until)
  const absentSet = new Set(data.absent_user_ids)
  const present = data.pilots.filter((p) => !absentSet.has(p.user_id))
  const absent = data.pilots.filter((p) => absentSet.has(p.user_id))

  async function undo() {
    setBusy(true)
    setError('')
    try {
      await api.undoAttendance()
      onChanged()
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <Placard title="حضور هذا الأسبوع" aside="مُسجَّل">
      <Row label="حاضرون" value={present.length} tone="taxi" />
      <Row label="غائبون" value={absent.length} tone="hold" />
      {absent.length ? (
        <p className="mt-2 text-[13px] text-muted">{absent.map((p) => p.full_name).join('، ')}</p>
      ) : null}
      {error && <p className="mt-3 text-[13px] text-hold">{error}</p>}
      {canUndo && (
        <button
          type="button"
          onClick={undo}
          disabled={busy}
          className="mt-4 min-h-[44px] w-full border border-hold text-[14px] text-hold disabled:opacity-50"
        >
          تراجع
        </button>
      )}
    </Placard>
  )
}
