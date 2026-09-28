import { api } from '../../api'
import type { OrgTahdirRow } from '../../api/types/adminQueue'
import { useAsync } from '../../state/useAsync'
import { Async } from '../../ui/Async'
import type { Column } from '../../ui/DataTable'
import DataTable from '../../ui/DataTable'

/**
 * تقرير تحضير القراءة — خمسة أعمدة فوق الحدّ، وبطاقةٌ لكل طالب تحته.
 *
 * و`struggling` يصل **محسوبًا من الخادم** فتُقرأ لهجتُه لا تُشتقّ هنا
 * (`AGENTS.md` ٥). والأحمر هنا مأذون بالفئة أ — «نتيجة سلبية في منطق
 * المنتج» (`VISUAL.md §٢`).
 */
const COLUMNS: Column<OrgTahdirRow>[] = [
  { id: 'name', header: 'الطالب', cell: (s) => s.full_name, primary: true },
  {
    id: 'percent',
    header: 'النسبة',
    numeric: true,
    cell: (s) => (
      <bdi dir="ltr" className={s.struggling ? 'text-(--color-red-text)' : 'text-(--color-accent)'}>
        {s.percent}%
      </bdi>
    ),
  },
  {
    id: 'days',
    header: 'الأيام',
    numeric: true,
    cell: (s) => (
      <>
        <bdi dir="ltr">{s.days_completed}</bdi>/٤
      </>
    ),
  },
  {
    id: 'pages',
    header: 'الصفحات',
    numeric: true,
    cell: (s) => <bdi dir="ltr">{s.pages_total}</bdi>,
  },
]

export default function TahdirReport() {
  const state = useAsync(() => api.admin.tahdirReport(), [])

  return (
    <div className="flex flex-col gap-3.5">
      <Async state={state} loadingTitle="تقرير تحضير القراءة">
        {(report) => (
          <DataTable
            columns={COLUMNS}
            rows={report.students}
            rowKey={(s) => s.user_id}
            caption="هذا الأسبوع"
            empty="لا طلاب نشِطون بعد."
          />
        )}
      </Async>
    </div>
  )
}
