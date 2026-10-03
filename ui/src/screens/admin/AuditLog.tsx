import { api } from '../../api'
import type { AuditEntry } from '../../api/types/audit'
import { useAsync } from '../../state/useAsync'
import { Async } from '../../ui/Async'
import type { Column } from '../../ui/DataTable'
import DataTable from '../../ui/DataTable'

/**
 * سجلّ التغييرات — `GET /admin/audit` (FR-084 · `SCOPE.md §٨` بند ١٥).
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
 * سجلّ التغييرات.
 *
 * **كان هذا الملفّ مسمًّى «الصندوق الأسود» خطأً** حتى و-٢١، و`SCOPE.md`
 * يقول غيره في موضعين: `§٨` بند ١٣ «الصندوق الأسود (**ملاحظة مجهولة**)»
 * و`§٩` يعدّه من صفحات **الطيّار**، أمّا «سجلّ التغييرات» فبند ١٥ من صفحات
 * المشرف. والوثيقة تعلو الكود (`AGENTS.md`) — فصُحِّحت التسمية، والصندوق
 * الأسود هو `Notes.tsx`.
 *
 * **وبلا مُرشِّح — قرارُ منتجٍ حُسم لا تأجيل.** النموذج يعرض أربعة مرشّحات
 * (الكلّ · اعتمادات · سلبي · إداري) على الشاشة التي كانت تحمل الاسم الخطأ.
 * وقرار المستخدم: «الصندوق الأسود ببساطة اقتراح مجهول الهوية، ويجيني أشوفه،
 * **فقط**» — فالمرشّحات أُسقِطت، ولم تكن `AuditEntry.kind` تحمل ما يقابلها
 * أصلًا (لا نوعَ «اعتماد» ولا «سلبي»).
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
            caption="الأحداث"
            empty="لا تغييرات بعد."
          />
        )}
      </Async>
    </div>
  )
}
