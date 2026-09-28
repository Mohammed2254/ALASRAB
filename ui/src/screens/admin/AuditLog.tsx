import { api } from '../../api'
import type { AuditEntry } from '../../api/types/audit'
import { useAsync } from '../../state/useAsync'
import { Async } from '../../ui/Async'
import type { Column } from '../../ui/DataTable'
import DataTable from '../../ui/DataTable'

/**
 * سجلّ التغييرات («الصندوق الأسود») — `GET /admin/audit` (FR-084).
 * **مفتوح لكل مشرف بلا حدّ سرب** — التعويض عن دمج الدورين (`AGENTS.md` ٩):
 * الحماية كشف الاستعمال لا منع الصلاحية. منظمة بلا تغييرات حالة مصمَّمة
 * لا خطأ (ق-٦١).
 */
const timeFormatter = new Intl.DateTimeFormat('ar-SA-u-ca-gregory-nu-latn', {
  day: 'numeric',
  month: 'long',
  hour: 'numeric',
  minute: 'numeric',
  timeZone: 'Asia/Riyadh',
})

const KIND_LABELS: Record<string, string> = {
  pin_reset: 'إعادة تعيين رمز',
  weights_version: 'إصدار أوزان',
  thresholds_update: 'تحديث العتبات',
  team_created: 'سرب جديد',
  team_archived: 'أرشفة سرب',
  membership_transferred: 'نقل طالب',
  quran_correction: 'تصحيح قرآني',
}

const COLUMNS: Column<AuditEntry>[] = [
  { id: 'summary', header: 'ما جرى', cell: (e) => e.summary, primary: true },
  {
    id: 'kind',
    header: 'النوع',
    cell: (e) => (
      <span className="text-(--color-text-dim)">{KIND_LABELS[e.kind] ?? e.kind}</span>
    ),
  },
  { id: 'actor', header: 'بواسطة', cell: (e) => e.actor_name },
  {
    id: 'at',
    header: 'الوقت',
    numeric: true,
    cell: (e) => <bdi dir="ltr">{timeFormatter.format(new Date(e.at))}</bdi>,
  },
]

/**
 * الصندوق الأسود.
 *
 * **بلا مُرشِّح بعد، عمدًا.** النموذج يعرض أربعة مرشّحات (الكلّ · اعتمادات ·
 * سلبي · إداري)، و`AuditEntry.kind` القائمة لا تحمل شيئًا يقابلها: لا نوعَ
 * «اعتماد» ولا «سلبي» فيها أصلًا. وتصنيفُ الأنواع الثمانية في تلك السلال
 * **اختراعُ تصنيفٍ للمنتج** لا عرضٌ له — فيُترك حتى يُقرَّر في `SCOPE.md`.
 */
export default function AuditLog() {
  const state = useAsync(() => api.admin.auditLog(), [])

  return (
    <div className="flex flex-col gap-3.5">
      <Async state={state} loadingTitle="سجلّ التغييرات">
        {(data) => (
          <DataTable
            columns={COLUMNS}
            rows={data.entries}
            rowKey={(e) => e.id}
            caption="التغييرات"
            empty="لا تغييرات بعد."
          />
        )}
      </Async>
    </div>
  )
}
