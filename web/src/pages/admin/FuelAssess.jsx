import { useState } from 'react'

import Placard, { Row } from '../../components/Placard'
import { Async } from '../../components/States'
import { api } from '../../lib/api'
import { useAsync } from '../../state/useAsync'

/*
  تقييم نشاط الوقود — و-٨ · FR-070 · FR-071.

  `team_id` صريح: المشرف على مستوى الجمعية يقيّم أيّ سرب (§٧.٣) لا سربه وحده.
  **`total_pct`/`litres` يعودان من الخادم بعد الحفظ** — لا حساب هنا.
*/

export default function FuelAssess({ onDone }) {
  const activitiesState = useAsync(() => api.fuelActivities(), [])
  const teamsState = useAsync(() => api.teams(), [])

  return (
    <div className="taxi-in mx-auto w-full max-w-[520px] px-4 pt-6 pb-10">
      <header className="mb-5 flex items-baseline gap-3">
        <h1 className="font-display text-[26px] leading-none">تقييم نشاط</h1>
        <span className="centerline" />
        <button
          type="button"
          onClick={onDone}
          className="min-h-[44px] shrink-0 px-2 text-[13px] text-muted"
        >
          رجوع
        </button>
      </header>

      <Async state={activitiesState} loadingTitle="تقييم نشاط">
        {(activityData) => (
          <Async state={teamsState} loadingTitle="تقييم نشاط">
            {(teamData) => (
              <Form activities={activityData.activities} teams={teamData.teams} />
            )}
          </Async>
        )}
      </Async>
    </div>
  )
}

function Form({ activities, teams }) {
  const [teamId, setTeamId] = useState('')
  const [activityId, setActivityId] = useState('')
  const [occurredOn, setOccurredOn] = useState('')
  const [scores, setScores] = useState({})
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const activity = activities.find((a) => String(a.id) === activityId)
  const activeTeams = teams.filter((t) => !t.archived_at)

  const selectActivity = (id) => {
    setActivityId(id)
    setScores({})
    setResult(null)
  }

  const ready =
    teamId && activityId && occurredOn.trim() && activity?.criteria.every((c) => scores[c.id]?.trim())

  async function submit() {
    setBusy(true)
    setError('')
    setResult(null)
    try {
      const body = {
        team_id: Number(teamId),
        activity_id: Number(activityId),
        occurred_on: occurredOn,
        scores: activity.criteria.map((c) => ({
          criterion_id: c.id,
          score_pct: scores[c.id],
        })),
      }
      setResult(await api.assessFuel(body))
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Placard title="تقييم جديد">
      <label htmlFor="fa_team" className="mb-1.5 block text-[13px]">
        السرب
      </label>
      <select
        id="fa_team"
        value={teamId}
        onChange={(e) => setTeamId(e.target.value)}
        className="mb-3 min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint"
      >
        <option value="">اختر سربًا</option>
        {activeTeams.map((t) => (
          <option key={t.id} value={t.id}>
            {t.name}
          </option>
        ))}
      </select>

      <label htmlFor="fa_activity" className="mb-1.5 block text-[13px]">
        النشاط
      </label>
      <select
        id="fa_activity"
        value={activityId}
        onChange={(e) => selectActivity(e.target.value)}
        className="mb-3 min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint"
      >
        <option value="">اختر نشاطًا</option>
        {activities.map((a) => (
          <option key={a.id} value={a.id}>
            {a.name}
          </option>
        ))}
      </select>

      <label htmlFor="fa_date" className="mb-1.5 block text-[13px]">
        تاريخ الوقوع
      </label>
      <input
        id="fa_date"
        type="date"
        value={occurredOn}
        onChange={(e) => setOccurredOn(e.target.value)}
        className="mb-4 min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint"
      />

      {activity && (
        <div className="mb-4">
          <p className="mb-2 text-[13px] text-muted">الدرجات</p>
          {activity.criteria.map((c) => (
            <div key={c.id} className="mb-2 flex items-baseline gap-3">
              <span className="shrink-0 text-[13px] text-muted">{c.name}</span>
              <span className="centerline" style={{ opacity: 0.45 }} />
              <input
                aria-label={`درجة ${c.name}`}
                value={scores[c.id] ?? ''}
                onChange={(e) => setScores((s) => ({ ...s, [c.id]: e.target.value }))}
                className="min-h-[44px] w-20 shrink-0 border border-concrete/45 bg-taxiway px-2 text-[14px] text-paint"
              />
            </div>
          ))}
        </div>
      )}

      {error && (
        <p role="alert" className="mb-3 text-[13px] text-hold">
          {error}
        </p>
      )}

      {result && (
        <Row
          label="نتيجة التقييم"
          value={<bdi dir="ltr">{result.litres} لتر</bdi>}
          tone="taxi"
        />
      )}

      <button
        type="button"
        disabled={busy || !ready}
        onClick={submit}
        className="mt-2 min-h-[48px] w-full border border-taxi bg-taxi text-[16px] text-asphalt disabled:opacity-40"
      >
        {busy ? 'جارٍ الحفظ…' : 'حفظ التقييم'}
      </button>
    </Placard>
  )
}
