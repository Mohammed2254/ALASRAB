import { api } from '../../api'
import { useAsync } from '../../state/useAsync'
import { Async } from '../../ui/Async'
import EmptyState from '../../ui/EmptyState'
import Placard from '../../ui/Placard'
import Prow from '../../ui/Prow'

/**
 * تقرير تحضير القراءة الأسبوعي — `GET /admin/tahdir/report` (FR-093).
 * **يشمل من لم يُرسل شيئًا** — تقريرٌ يستبعد الغائبين يخفي بالضبط من
 * يحتاج المشرف رؤيته.
 */
export default function TahdirReport() {
  const state = useAsync(() => api.admin.tahdirReport(), [])

  return (
    <div className="flex flex-col gap-3.5">
      <Async state={state} loadingTitle="تقرير تحضير القراءة">
        {(report) =>
          report.students.length === 0 ? (
            <Placard title="الطلاب">
              <EmptyState>لا طلاب نشِطون بعد.</EmptyState>
            </Placard>
          ) : (
            <Placard title="هذا الأسبوع">
              {report.students.map((s) => (
                <div key={s.user_id} className="mb-2 border-b border-(--color-border) pb-2 last:border-none">
                  <Prow
                    label={s.full_name}
                    value={<bdi dir="ltr">{s.percent}%</bdi>}
                    tone={s.struggling ? 'red' : 'accent'}
                  />
                  <p className="text-[12px] text-(--color-text-dim)">
                    <bdi dir="ltr">{s.days_completed}</bdi>/٤ أيام · <bdi dir="ltr">{s.pages_total}</bdi> صفحة
                  </p>
                </div>
              ))}
            </Placard>
          )
        }
      </Async>
    </div>
  )
}
