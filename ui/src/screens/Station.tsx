import { api } from '../api'
import { fmtDecimal } from '../api/format'
import { useAsync } from '../state/useAsync'
import { Async } from '../ui/Async'
import EmptyState from '../ui/EmptyState'
import FuelDial from '../ui/FuelDial'
import Pill from '../ui/Pill'
import Placard from '../ui/Placard'
import Prow from '../ui/Prow'

/**
 * محطة التزوّد — `GET /station` (FR-072). شاشة طيّار لا مشرف: كل عضو سرب
 * يراها (`API.md` §`GET /station`).
 *
 * **لا عدّاد نسبة أسبوعية حيّة** (تصحيحٌ عن النموذج المعتمد، `و-١٥.md` §١.٢):
 * العقد الفعليّ يحمل `litres` تراكميّة و`recent[]` تاريخيّة فقط — لا مفهوم
 * "نسبة السرب هذا الأسبوع" في الخادم. `FuelDial` هنا لآخر تقييم حقيقيّ في
 * `recent[0]`، لا لمتوسّطٍ مُفترَض.
 */

const dayFormatter = new Intl.DateTimeFormat('ar-SA-u-ca-gregory-nu-latn', {
  day: 'numeric',
  month: 'long',
  timeZone: 'Asia/Riyadh',
})
const formatDay = (iso: string) => dayFormatter.format(new Date(`${iso}T00:00:00Z`))

export default function Station() {
  const state = useAsync(() => api.me.station(), [])

  return (
    <Async state={state} loadingTitle="محطة التزوّد">
      {(data) => {
        if (!data.team) {
          return (
            <Placard title="السرب">
              <EmptyState>لست في سرب حاليًّا. راجع المشرف.</EmptyState>
            </Placard>
          )
        }

        const latest = data.recent.at(0)

        return (
          <div className="flex flex-col gap-3.5">
            {/* مهمّة هذا الأسبوع — النموذج يُريها للطالب **قبل** الاعتماد.
                واللترات هنا متوقَّعة لا محتسَبة حتى يُعتمد الأسبوع، فالشارة
                هي ما يفصل بينهما. والأخضر على «مُعتمَد» مأذون: حالةٌ نشطة. */}
            {data.week_task ? (
              <Placard
                title={`مهمّة هذا الأسبوع: ${data.week_task.name}`}
                aside={
                  data.week_task.state === 'approved' ? (
                    <Pill tone="green">معتمَد</Pill>
                  ) : (
                    <Pill tone="accent">مسوّدة — بانتظار اعتماد المشرف</Pill>
                  )
                }
              >
                {data.week_task.assessed ? (
                  <>
                    <Prow
                      label="النسبة"
                      value={<bdi dir="ltr">{fmtDecimal(data.week_task.total_pct)}٪</bdi>}
                      tone="accent"
                    />
                    <Prow
                      label={
                        data.week_task.state === 'approved'
                          ? 'لترات هذه المهمّة'
                          : 'لترات متوقَّعة — لم تُحتسب بعد'
                      }
                      value={<bdi dir="ltr">{fmtDecimal(data.week_task.litres)}</bdi>}
                    />
                  </>
                ) : (
                  <p className="py-2 text-[13px] text-(--color-text-dim)">
                    لم تُقيَّم بعد — هذه مهمّة سربكم لهذا الأسبوع.
                  </p>
                )}
              </Placard>
            ) : null}

            <Placard title={data.team.name} aside="وقود السرب">
              <Prow label="اللترات" value={<bdi dir="ltr">{fmtDecimal(data.team.litres)}</bdi>} tone="accent" />
              {data.tank_capacity_l ? (
                <Prow label="سعة الخزّان" value={<bdi dir="ltr">{fmtDecimal(data.tank_capacity_l)}</bdi>} />
              ) : null}
            </Placard>

            {latest ? (
              <Placard title="آخر تقييم" aside={formatDay(latest.occurred_on)}>
                <div className="mx-auto max-w-[220px] text-center">
                  <FuelDial pct={latest.total_pct} />
                  <p className="num text-[26px] font-extrabold text-(--color-accent)">
                    <bdi dir="ltr">{fmtDecimal(latest.total_pct)}٪</bdi>
                  </p>
                </div>
                <Prow label={latest.activity_name} value={<bdi dir="ltr">{fmtDecimal(latest.litres)}</bdi>} tone="accent" />
              </Placard>
            ) : null}

            <Placard title="آخر التقييمات">
              {data.recent.length ? (
                data.recent.map((r, i) => (
                  <Prow
                    key={i}
                    label={r.activity_name}
                    value={<bdi dir="ltr">{fmtDecimal(r.litres)}</bdi>}
                    tone="accent"
                    sub={
                      <span>
                        {formatDay(r.occurred_on)} · <bdi dir="ltr">{fmtDecimal(r.total_pct)}٪</bdi>
                      </span>
                    }
                  />
                ))
              ) : (
                <EmptyState>لا تقييمات بعد.</EmptyState>
              )}
            </Placard>
          </div>
        )
      }}
    </Async>
  )
}
