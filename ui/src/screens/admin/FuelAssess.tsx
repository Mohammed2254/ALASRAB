import { useState } from 'react'

import { api, ApiError } from '../../api'
import { fmtDecimal } from '../../api/format'
import type { ActivityRow, ScoreRowForm } from '../../api/types/fuel'
import type { AdminTeamRow } from '../../api/types/teams'
import { useAsync } from '../../state/useAsync'
import { Async } from '../../ui/Async'
import Button from '../../ui/Button'
import Field from '../../ui/Field'
import Placard from '../../ui/Placard'
import Prow from '../../ui/Prow'

/**
 * تقييم نشاط الوقود — `POST /admin/fuel/assess` (FR-070 · FR-071).
 * `team_id` صريح — المشرف على مستوى الجمعية يقيّم أيّ سرب (`AGENTS.md` ٩).
 * **`total_pct`/`litres` يعودان من الخادم بعد الحفظ** — لا حساب هنا.
 */
const fieldClass = 'min-h-[48px] w-full rounded-(--radius-sm) border border-(--color-border-strong) bg-(--color-bg-2) px-3 text-[16px] text-(--color-text)'

function Form({ activities, teams }: { activities: ActivityRow[]; teams: AdminTeamRow[] }) {
  const [teamId, setTeamId] = useState('')
  const [activityId, setActivityId] = useState('')
  const [occurredOn, setOccurredOn] = useState('')
  const [scores, setScores] = useState<Record<number, string>>({})
  const [resultLitres, setResultLitres] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const activity = activities.find((a) => String(a.id) === activityId)
  const activeTeams = teams.filter((t) => !t.archived_at)

  const selectActivity = (id: string) => {
    setActivityId(id)
    setScores({})
    setResultLitres(null)
  }

  const ready = teamId && activityId && occurredOn.trim() && activity?.criteria.every((c) => scores[c.id]?.trim())

  async function submit() {
    if (!activity) return
    setBusy(true)
    setError('')
    setResultLitres(null)
    try {
      const scoreRows: ScoreRowForm[] = activity.criteria.map((c) => ({ criterion_id: c.id, score_pct: scores[c.id] ?? '' }))
      const result = await api.admin.assessFuel({ team_id: teamId, activity_id: activityId, occurred_on: occurredOn, scores: scoreRows })
      setResultLitres(fmtDecimal(result.litres))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Placard title="تقييم جديد">
      <Field label="السرب" htmlFor="fa_team">
        <select id="fa_team" value={teamId} onChange={(e) => setTeamId(e.target.value)} className={fieldClass}>
          <option value="">اختر سربًا</option>
          {activeTeams.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
      </Field>
      <Field label="النشاط" htmlFor="fa_activity">
        <select id="fa_activity" value={activityId} onChange={(e) => selectActivity(e.target.value)} className={fieldClass}>
          <option value="">اختر نشاطًا</option>
          {activities.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </select>
      </Field>
      <Field label="تاريخ الوقوع" htmlFor="fa_date">
        <input id="fa_date" type="date" value={occurredOn} onChange={(e) => setOccurredOn(e.target.value)} className={fieldClass} />
      </Field>

      {activity ? (
        <div className="mb-4">
          <p className="mb-2 text-[13px] text-(--color-text-dim)">الدرجات</p>
          {activity.criteria.map((c) => (
            <div key={c.id} className="mb-2 flex items-baseline gap-3">
              <span className="min-w-0 flex-1 text-[13px] text-(--color-text-dim)">{c.name}</span>
              <input
                aria-label={`درجة ${c.name}`}
                value={scores[c.id] ?? ''}
                onChange={(e) => setScores((s) => ({ ...s, [c.id]: e.target.value }))}
                className="min-h-[44px] w-20 shrink-0 rounded-(--radius-sm) border border-(--color-border-strong) bg-(--color-bg-2) px-2 text-[14px] text-(--color-text)"
              />
            </div>
          ))}
        </div>
      ) : null}

      {error ? (
        <p role="alert" className="mb-3 text-[13px] text-(--color-red-text)">
          {error}
        </p>
      ) : null}
      {resultLitres ? <Prow label="نتيجة التقييم" value={<bdi dir="ltr">{resultLitres} لتر</bdi>} tone="accent" /> : null}

      <Button disabled={busy || !ready} onClick={submit} className="mt-2 w-full">
        {busy ? 'جارٍ الحفظ…' : 'حفظ التقييم'}
      </Button>
    </Placard>
  )
}

export default function FuelAssess() {
  const activitiesState = useAsync(() => api.admin.fuelActivities(), [])
  const teamsState = useAsync(() => api.admin.teams(), [])

  return (
    <div className="flex flex-col gap-3.5">
      <Async state={activitiesState} loadingTitle="تقييم نشاط">
        {(activityData) => (
          <Async state={teamsState} loadingTitle="تقييم نشاط">
            {(teamData) => <Form activities={activityData.activities} teams={teamData.teams} />}
          </Async>
        )}
      </Async>
    </div>
  )
}
