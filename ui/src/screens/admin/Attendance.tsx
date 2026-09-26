import { useState } from 'react'

import { api, ApiError } from '../../api'
import type { AttendanceStatus, PilotRosterRow } from '../../api/types/attendance'
import { go } from '../../nav/history'
import { useAsync } from '../../state/useAsync'
import { Async } from '../../ui/Async'
import Button from '../../ui/Button'
import Placard from '../../ui/Placard'
import Prow from '../../ui/Prow'
import Subback from '../../ui/Subback'

/**
 * الحضور اليدويّ — `GET/POST /admin/attendance*` (FR-041/042، احتياطيّ).
 * **الجميع حاضر افتراضًا**: الشاشة تفتح وكل زرّ بلون الحضور، والمشرف ينقر
 * الغائب وحده. `hours_each` يصل جاهزًا من الخادم (وزن الحضور الفعليّ، لا
 * رقم في الكود). حالتان صريحتان يفرضهما `already_recorded` من الخادم.
 */
function RollCall({ pilots, onRecorded }: { pilots: PilotRosterRow[]; onRecorded: () => void }) {
  const [absentIds, setAbsentIds] = useState<number[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  function toggle(id: number) {
    setAbsentIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  async function submit() {
    setBusy(true)
    setError('')
    try {
      await api.admin.recordAttendance(absentIds)
      onRecorded()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
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
              className={`flex min-h-[44px] w-full items-center justify-between gap-3 rounded-(--radius-sm) border px-3 text-[14px] ${
                absent ? 'border-(--color-red) text-(--color-red-text)' : 'border-(--color-accent) text-(--color-accent)'
              }`}
            >
              <span>{p.full_name}</span>
              <span>{absent ? 'غائب' : 'حاضر'}</span>
            </button>
          )
        })}
      </div>
      {error ? (
        <p role="alert" className="mt-3 text-[13px] text-(--color-red-text)">
          {error}
        </p>
      ) : null}
      <Button disabled={busy} onClick={submit} className="mt-4 w-full">
        حفظ الحضور
      </Button>
    </Placard>
  )
}

function Recorded({ data, onChanged }: { data: AttendanceStatus; onChanged: () => void }) {
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
      await api.admin.undoAttendance()
      onChanged()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
      setBusy(false)
    }
  }

  return (
    <Placard title="حضور هذا الأسبوع" aside="مُسجَّل">
      <Prow label="حاضرون" value={present.length} tone="accent" />
      <Prow label="غائبون" value={absent.length} tone={absent.length ? 'red' : undefined} />
      {absent.length ? <p className="mt-2 text-[13px] text-(--color-text-dim)">{absent.map((p) => p.full_name).join('، ')}</p> : null}
      {error ? (
        <p role="alert" className="mt-3 text-[13px] text-(--color-red-text)">
          {error}
        </p>
      ) : null}
      {canUndo ? (
        <Button variant="danger" disabled={busy} onClick={undo} className="mt-4 w-full">
          تراجع
        </Button>
      ) : null}
    </Placard>
  )
}

export default function Attendance() {
  const state = useAsync(() => api.admin.attendance(), [])

  return (
    <div className="flex flex-col gap-3.5">
      <Subback label="الرئيسية" onClick={() => go('deck')} />
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
