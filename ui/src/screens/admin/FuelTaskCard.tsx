import { useState } from 'react'

import { api, ApiError } from '../../api'
import { fmtDecimal } from '../../api/format'
import type { FuelWeek, WeekTask } from '../../api/types/fuel'
import Button from '../../ui/Button'
import Placard from '../../ui/Placard'
import Prow from '../../ui/Prow'
import ErrorText from '../../ui/ErrorText'

/**
 * بطاقة مهمّةٍ واحدة في أسبوع الوقود — تعيينُ سربها ودرجاتُها وإزالتُها.
 *
 * **الدرجات تُحرَّر محليًّا وتُحفَظ بضغطة**: نداءٌ لكل ضغطة مفتاح يجعل شبكةً
 * بطيئة تبدو واجهةً مكسورة. وكلُّ تعديلٍ يُرجع الأسبوع كاملًا من الخادم،
 * فالشاشة لا تعيد الحساب ولا تخمّن الحالة الجديدة.
 *
 * فُصلت عن الشاشة في مراجعة و-٢٠ — تحرير مهمّةٍ شيء، وتصفّحُ أسبوعٍ واعتمادُه
 * شيءٌ آخر.
 */
export default function TaskCard({
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

      {error ? <ErrorText spacing="mt-2">{error}</ErrorText> : null}
    </Placard>
  )
}

