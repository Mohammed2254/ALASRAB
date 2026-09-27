import { api } from '../../api'
import { useAsync } from '../../state/useAsync'
import { Async } from '../../ui/Async'
import EmptyState from '../../ui/EmptyState'
import Placard from '../../ui/Placard'

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

export default function AuditLog() {
  const state = useAsync(() => api.admin.auditLog(), [])

  return (
    <div className="flex flex-col gap-3.5">
      <Async state={state} loadingTitle="سجلّ التغييرات">
        {(data) =>
          data.entries.length ? (
            <Placard title="التغييرات" aside={`الأحدث أوّلًا · ${data.entries.length}`}>
              {data.entries.map((e) => (
                <div key={e.id} className="mb-2 border-b border-(--color-border) pb-2 last:border-none">
                  <div className="flex items-baseline justify-between gap-2.5">
                    <span className="text-[13px] text-(--color-text-dim)">{KIND_LABELS[e.kind] ?? e.kind}</span>
                    <span className="text-[12px] text-(--color-text-dim)">{timeFormatter.format(new Date(e.at))}</span>
                  </div>
                  <p className="text-[13px] text-(--color-text)">{e.summary}</p>
                  <p className="text-[12px] text-(--color-text-dim)">بواسطة {e.actor_name}</p>
                </div>
              ))}
            </Placard>
          ) : (
            <Placard title="التغييرات">
              <EmptyState>لا تغييرات بعد.</EmptyState>
            </Placard>
          )
        }
      </Async>
    </div>
  )
}
