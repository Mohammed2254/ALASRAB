import { useState } from 'react'

import { api, ApiError } from '../../api'
import { fmtDecimal } from '../../api/format'
import type { CriterionRowForm, FuelWeek, FuelWeekState, WeekTask } from '../../api/types/fuel'
import { useAsync } from '../../state/useAsync'
import { Async } from '../../ui/Async'
import Button from '../../ui/Button'
import EmptyState from '../../ui/EmptyState'
import Field from '../../ui/Field'
import Placard from '../../ui/Placard'
import Pill from '../../ui/Pill'
import Prow from '../../ui/Prow'

/**
 * أنشطة الوقود وبنودها — `GET/POST /admin/fuel/activities` (بنية تحتية
 * لـFR-070). **إنشاءٌ جديد لا تعديل**: الخادم يرفض بنودًا لا تجمع ١٠٠٪
 * بالضبط (ث-١٠أ) — لا حساب مجموع هنا (`AGENTS.md` ٥).
 */
const fieldClass = 'min-h-[48px] w-full rounded-(--radius-sm) border border-(--color-border-strong) bg-(--color-bg-2) px-3 text-[16px] text-(--color-text)'
const rowInputClass = 'min-h-[44px] w-1/3 min-w-0 rounded-(--radius-sm) border border-(--color-border-strong) bg-(--color-bg-2) px-2 text-[14px] text-(--color-text)'

function NewActivityForm({ onCreated }: { onCreated: () => void }) {
  const [key, setKey] = useState('')
  const [name, setName] = useState('')
  const [litresFull, setLitresFull] = useState('')
  const [criteria, setCriteria] = useState<CriterionRowForm[]>([{ key: '', name: '', weight_pct: '' }])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const update = (i: number, field: keyof CriterionRowForm, value: string) =>
    setCriteria((rows) => rows.map((r, idx) => (idx === i ? { ...r, [field]: value } : r)))

  const ready =
    key.trim() && name.trim() && litresFull.trim() && criteria.every((c) => c.key.trim() && c.name.trim() && c.weight_pct.trim())

  async function submit() {
    setBusy(true)
    setError('')
    try {
      await api.admin.createFuelActivity({
        key: key.trim(),
        name: name.trim(),
        litres_full: litresFull,
        criteria: criteria.map((c) => ({ key: c.key.trim(), name: c.name.trim(), weight_pct: c.weight_pct })),
      })
      setKey('')
      setName('')
      setLitresFull('')
      setCriteria([{ key: '', name: '', weight_pct: '' }])
      onCreated()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Placard title="نشاط جديد">
      <Field label="المفتاح" htmlFor="fa_key">
        <input id="fa_key" value={key} onChange={(e) => setKey(e.target.value)} className={fieldClass} />
      </Field>
      <Field label="الاسم" htmlFor="fa_name">
        <input id="fa_name" value={name} onChange={(e) => setName(e.target.value)} className={fieldClass} />
      </Field>
      <Field label="السعة الكاملة (لتر)" htmlFor="fa_litres">
        <input id="fa_litres" value={litresFull} onChange={(e) => setLitresFull(e.target.value)} className={fieldClass} />
      </Field>

      <p className="mb-2 text-[13px] text-(--color-text-dim)">البنود</p>
      {criteria.map((c, i) => (
        <div key={i} className="mb-2 flex gap-2">
          <input aria-label="مفتاح البند" value={c.key} onChange={(e) => update(i, 'key', e.target.value)} className={rowInputClass} />
          <input aria-label="اسم البند" value={c.name} onChange={(e) => update(i, 'name', e.target.value)} className={rowInputClass} />
          <input aria-label="وزن البند" value={c.weight_pct} onChange={(e) => update(i, 'weight_pct', e.target.value)} className={rowInputClass} />
        </div>
      ))}
      <button
        type="button"
        onClick={() => setCriteria((rows) => [...rows, { key: '', name: '', weight_pct: '' }])}
        className="mb-4 min-h-[44px] w-full rounded-(--radius-sm) border border-(--color-border-strong) text-[13px] text-(--color-text-dim)"
      >
        + بند جديد
      </button>

      {error ? (
        <p role="alert" className="mb-3 text-[13px] text-(--color-red-text)">
          {error}
        </p>
      ) : null}

      <Button disabled={busy || !ready} onClick={submit} className="w-full">
        {busy ? 'جارٍ الإنشاء…' : 'إنشاء نشاط'}
      </Button>
    </Placard>
  )
}

/**
 * شارة حالة الأسبوع — **حقلٌ من الخادم لا استنتاج من فراغ الدرجات.**
 *
 * والأخضر هنا مأذون: «مُعتمَد» حالةٌ **نشطة** بالمعنى المقنَّن في
 * `VISUAL.md §٢` — الأسبوع صبّ في وقود الأسراب فعلًا.
 */
function StateBadge({ state }: { state: FuelWeekState }) {
  if (state === 'approved') return <Pill tone="green">مُعتمَد</Pill>
  if (state === 'draft') return <Pill tone="accent">مسوّدة</Pill>
  return <Pill tone="muted">لم يُفتح بعد</Pill>
}

function TaskCard({
  task,
  week,
  locked,
  onChanged,
}: {
  task: WeekTask
  week: FuelWeek
  locked: boolean
  onChanged: (next: FuelWeek) => void
}) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  // الدرجات تُحرَّر محليًّا ثم تُحفَظ — لا نداء لكل ضغطة مفتاح.
  const [scores, setScores] = useState<Record<number, string>>(() =>
    Object.fromEntries(task.criteria.map((c) => [c.id, c.score_pct ?? '']))
  )

  async function run(action: () => Promise<FuelWeek>) {
    setBusy(true)
    setError('')
    try {
      onChanged(await action())
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
    } finally {
      setBusy(false)
    }
  }

  const filled = task.criteria.filter((c) => scores[c.id]?.trim())

  return (
    <Placard
      title={task.name}
      aside={task.assessed ? <bdi dir="ltr">{fmtDecimal(task.total_pct)}%</bdi> : 'بلا تقييم'}
    >
      {task.criteria.map((c) => (
        <div key={c.id} className="mb-2 flex min-w-0 items-center gap-2">
          <span className="min-w-0 flex-1 text-[13px]">
            {c.name} <span className="text-(--color-text-dim)">(<bdi dir="ltr">{fmtDecimal(c.weight_pct)}%</bdi>)</span>
          </span>
          <input
            type="number"
            inputMode="decimal"
            aria-label={`درجة ${c.name}`}
            disabled={locked}
            value={scores[c.id] ?? ''}
            onChange={(e) => setScores((prev) => ({ ...prev, [c.id]: e.target.value }))}
            className="min-h-[44px] w-[92px] shrink-0 rounded-(--radius-sm) border border-(--color-border-strong) bg-(--color-bg-2) px-2 text-[14px] text-(--color-text)"
          />
        </div>
      ))}

      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-(--color-border) pt-3">
        <label className="text-[12px] text-(--color-text-dim)" htmlFor={`team_${task.activity_id}`}>
          لسرب:
        </label>
        <select
          id={`team_${task.activity_id}`}
          disabled={locked}
          value={task.team_id ?? ''}
          onChange={(e) =>
            run(() =>
              api.admin.assignFuelTeam(task.activity_id, e.target.value, week.week_start)
            )
          }
          className="min-h-[44px] min-w-0 flex-1 rounded-(--radius-sm) border border-(--color-border-strong) bg-(--color-bg-2) px-2 text-[13px] text-(--color-text)"
        >
          <option value="">بلا تعيين</option>
          {week.teams.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>

        {locked ? null : (
          <>
            <Button
              disabled={busy || filled.length === 0}
              onClick={() =>
                run(() =>
                  api.admin.saveFuelScores(
                    task.activity_id,
                    filled.map((c) => ({ criterion_id: c.id, score_pct: scores[c.id] ?? '' })),
                    week.week_start
                  )
                )
              }
            >
              حفظ التقييم
            </Button>
            <button
              type="button"
              disabled={busy}
              onClick={() => run(() => api.admin.removeFuelTask(task.activity_id, week.week_start))}
              className="min-h-[44px] rounded-(--radius-sm) border border-(--color-red) px-3 text-[12px] font-semibold text-(--color-red-text)"
            >
              إزالة
            </button>
          </>
        )}
      </div>

      {task.assessed ? (
        <Prow
          label="لترات هذه المهمّة"
          value={<bdi dir="ltr">{fmtDecimal(task.litres)}</bdi>}
          tone="accent"
        />
      ) : null}

      {error ? (
        <p role="alert" className="mt-2 text-[13px] text-(--color-red-text)">
          {error}
        </p>
      ) : null}
    </Placard>
  )
}

/**
 * أنشطة الوقود — **شاشة الأسبوع** (و-٢٠).
 *
 * كانت قائمةَ أنشطةٍ ونموذجَ إنشاء فقط. والنموذج المعتمد يجعلها مهامَّ أسبوعٍ
 * بعينه: تعيينُ سربٍ لكل مهمّة، ودرجاتٌ **مسوّدة**، وإضافةٌ وإزالةٌ **لهذا
 * الأسبوع وحده**، ثم اعتمادٌ واحد يصبّ في وقود كل سرب.
 *
 * والتنقّل بين الأسابيع ليس زينة: التقييم قد يتأخّر، فيرجع المشرف إلى أسبوعٍ
 * مضى ويقيّمه **بتاريخه هو** — والخادم يؤرّخ الأحداث ببداية ذلك الأسبوع.
 *
 * ولا حساب هنا: النسبة واللترات وحالةُ الأسبوع كلّها تصل محسوبة.
 */
export default function FuelActivities() {
  const [weekStart, setWeekStart] = useState<string | undefined>(undefined)
  const state = useAsync(() => api.admin.fuelWeek(weekStart), [weekStart])
  const [week, setWeek] = useState<FuelWeek | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const shown = week ?? null

  async function approve(current: FuelWeek) {
    setBusy(true)
    setError('')
    try {
      setWeek(await api.admin.approveFuelWeek(current.week_start))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-3.5">
      <Async state={state} loadingTitle="أسبوع الوقود">
        {(loaded) => {
          const data = shown && shown.week_start === loaded.week_start ? shown : loaded
          const locked = data.state === 'approved'
          return (
            <div className="flex flex-col gap-3.5">
              <Placard
                title="أسبوع الوقود"
                aside={<StateBadge state={data.state} />}
              >
                <Field label="أسبوع التقييم — غيّره لتقييم أسبوعٍ مضى" htmlFor="fuel_week">
                  <input
                    id="fuel_week"
                    type="date"
                    value={data.week_start}
                    onChange={(e) => {
                      setWeek(null)
                      setWeekStart(e.target.value)
                    }}
                    className={fieldClass}
                  />
                </Field>
                <p className="text-[12px] text-(--color-text-dim)">
                  الدرجات مسوّدة لا أثر لها، والاعتماد وحده يصبّ في وقود الأسراب — بتاريخ هذا
                  الأسبوع لا بتاريخ اليوم. ولكل سرب مهمّة واحدة عادةً، وليس ذلك إلزامًا.
                </p>
              </Placard>

              {data.tasks.length ? (
                data.tasks.map((task) => (
                  <TaskCard
                    key={task.activity_id}
                    task={task}
                    week={data}
                    locked={locked}
                    onChanged={setWeek}
                  />
                ))
              ) : (
                <Placard title="مهامّ هذا الأسبوع">
                  <EmptyState>لا مهامّ في هذا الأسبوع.</EmptyState>
                </Placard>
              )}

              {error ? (
                <p role="alert" className="text-[13px] text-(--color-red-text)">
                  {error}
                </p>
              ) : null}

              {locked ? (
                <p className="text-[13px] text-(--color-text-dim)">
                  اعتُمد هذا الأسبوع — لا يُعدَّل بعد الاعتماد.
                </p>
              ) : (
                <Button disabled={busy} onClick={() => approve(data)} className="w-full">
                  {busy ? 'جارٍ الاعتماد…' : 'اعتماد أسبوع الوقود — يصبّ في وقود كل سرب'}
                </Button>
              )}

              <NewActivityForm onCreated={() => setWeekStart(data.week_start)} />
            </div>
          )
        }}
      </Async>
    </div>
  )
}
