
import { api } from '../../api'
import type { RosterRow } from '../../api/types/roster'
import { useAsync } from '../../state/useAsync'
import { Async } from '../../ui/Async'
import type { Column } from '../../ui/DataTable'
import DataTable from '../../ui/DataTable'
import Pill from '../../ui/Pill'
import Placard from '../../ui/Placard'
import Prow from '../../ui/Prow'
import NewStudentForm from './NewStudentForm'
import StudentRowActions from './StudentRowActions'

/**
 * الطلاب — `GET/POST/PATCH /admin/users*` (و-٢١).
 *
 * **الشاشة التي لم تكن**: لا بند في `SCOPE.md` لإنشاء طالب (فيه `FR-004`
 * لإعادة تعيين الرمز و`FR-083` لإدارة الأسراب)، وكان الكاتب الوحيد لـ`User`
 * في المشروع كلّه هو `seed.py` — وهو يرفض الإنتاج. فقاعدةٌ منشورة جديدة كانت
 * بلا أيّ طريق إلى طالب، وشاشةُ الدخول تردّ ٤٠١ للأبد.
 *
 * **والمعطَّلون معروضون مُعلَّمين لا مخفيّين:** مشرفٌ لا يرى المعطَّل لا
 * يستطيع إعادة تفعيله، فيُعيد إنشاءه برقمٍ آخر — ويتشظّى تاريخ الطالب بين
 * حسابين، وهو عطلٌ لا رجعة فيه في الدفتر (ADR-004).
 *
 * ولا حساب هنا: الأدوار والحالات حقولٌ تصل من الخادم.
 */
const ROLE_LABEL: Record<string, string> = { admin: 'مشرف', pilot: 'طيار' }

export default function Students() {
  const roster = useAsync(() => api.admin.roster(), [])
  const teams = useAsync(() => api.admin.teams(), [])

  const columns: Column<RosterRow>[] = [
    { id: 'name', header: 'الطالب', cell: (r) => r.full_name, primary: true },
    {
      id: 'no',
      header: 'رقم الدخول',
      numeric: true,
      cell: (r) => <bdi dir="ltr">{r.student_no}</bdi>,
    },
    { id: 'team', header: 'السرب', cell: (r) => r.team_name ?? 'بلا سرب' },
    { id: 'role', header: 'الدور', cell: (r) => ROLE_LABEL[r.role] ?? r.role },
    {
      id: 'state',
      header: 'الحالة',
      // الأخضر مأذون: «نشط» هو المعنى المقنَّن له حرفيًّا (`VISUAL.md §٢`).
      cell: (r) => (r.is_active ? <Pill tone="green">نشط</Pill> : <Pill tone="muted">معطَّل</Pill>),
    },
  ]

  return (
    <div className="flex flex-col gap-3.5">
      <Async state={roster} loadingTitle="الطلاب">
        {(data) => (
          <DataTable
            columns={columns}
            rows={data.students}
            rowKey={(r) => r.id}
            caption="سجلّ الطلاب"
            empty="لا طلاب بعد — أضِفهم أدناه."
            action={(row) => <StudentRowActions row={row} onChanged={roster.reload} />}
          />
        )}
      </Async>

      <Async state={teams} loadingTitle="الأسراب">
        {(data) =>
          data.teams.length ? (
            <NewStudentForm teams={data.teams} onCreated={roster.reload} />
          ) : (
            // سببٌ صريح لا نموذجٌ معطَّل بلا تفسير: العضوية تحتاج سربًا
            // (`memberships.team_id` غير قابل للعدم).
            <Placard title="إضافة طالب">
              <Prow label="لا سرب بعد" value="أنشئ سربًا أوّلًا من شاشة الأسراب" />
            </Placard>
          )
        }
      </Async>
    </div>
  )
}
