import { useState } from 'react'

import { api, ApiError } from '../../api'
import type { FuelWeek, FuelWeekState } from '../../api/types/fuel'
import { useAsync } from '../../state/useAsync'
import { Async } from '../../ui/Async'
import Button from '../../ui/Button'
import EmptyState from '../../ui/EmptyState'
import Field from '../../ui/Field'
import Placard from '../../ui/Placard'
import FuelTaskCard from './FuelTaskCard'
import NewActivityForm from './NewActivityForm'
import Pill from '../../ui/Pill'

/**
 * أنشطة الوقود وبنودها — `GET/POST /admin/fuel/activities` (بنية تحتية
 * لـFR-070). **إنشاءٌ جديد لا تعديل**: الخادم يرفض بنودًا لا تجمع ١٠٠٪
 * بالضبط (ث-١٠أ) — لا حساب مجموع هنا (`AGENTS.md` ٥).
 */
const fieldClass = 'min-h-[48px] w-full rounded-(--radius-sm) border border-(--color-border-strong) bg-(--color-bg-2) px-3 text-[16px] text-(--color-text)'

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
          // ردُّ آخر تعديل يغلب المحمَّل ما دام لنفس الأسبوع — فلا جلبٌ
          // ثانٍ بعد كل حفظ. وتغييرُ الأسبوع يُصفّر `week` فيعود المحمَّل.
          const data = week && week.week_start === loaded.week_start ? week : loaded
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
                  <FuelTaskCard
                    // المفتاح يحمل الأسبوع **احتياطًا لا إصلاحًا**: اليوم
                    // يُفكَّك المكوّن أصلًا عند تبديل الأسبوع لأن `useAsync`
                    // يمرّ بحالة تحميل، فتُصفَّر الدرجات المحليّة. ولو حُفظت
                    // البيانات القديمة أثناء الجلب يومًا (تحميلٌ بلا وميض)،
                    // لصار المفتاح هو ما يمنع ظهور درجات أسبوعٍ على آخر.
                    key={`${data.week_start}:${task.activity_id}`}
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
