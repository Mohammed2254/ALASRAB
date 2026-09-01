import Placard, { Row } from '../../components/Placard'
import { Async, Empty } from '../../components/States'
import { api } from '../../lib/api'
import { useAsync } from '../../state/useAsync'

/*
  سجلّ التغييرات — و-٧ · FR-084.

  **مفتوح لكل مشرف بلا حدّ سرب** — التعويض عن دمج الدورين (`ARCHITECTURE.md`
  §٧.٣): الحماية كشف الاستعمال لا منع الصلاحية، فترى هنا فعل كل مشرف لا فعلك
  وحدك. والحالة الفارغة صريحة (ق-٦١) — منظمة بلا تغييرات ليست خللًا.
*/

const timeFormatter = new Intl.DateTimeFormat('ar-SA-u-ca-gregory-nu-latn', {
  day: 'numeric',
  month: 'long',
  hour: 'numeric',
  minute: 'numeric',
  timeZone: 'Asia/Riyadh',
})

const KIND_LABELS = {
  pin_reset: 'إعادة تعيين رمز',
  weights_version: 'إصدار أوزان',
  thresholds_update: 'تحديث العتبات',
  team_created: 'سرب جديد',
  team_archived: 'أرشفة سرب',
  membership_transferred: 'نقل طالب',
  quran_correction: 'تصحيح قرآني',
}

export default function AuditLog({ onDone }) {
  const state = useAsync(() => api.auditLog(), [])

  return (
    <div className="taxi-in mx-auto w-full max-w-[520px] px-4 pt-6 pb-10">
      <header className="mb-5 flex items-baseline gap-3">
        <h1 className="font-display text-[26px] leading-none">سجلّ التغييرات</h1>
        <span className="centerline" />
        <button
          type="button"
          onClick={onDone}
          className="min-h-[44px] shrink-0 px-2 text-[13px] text-muted"
        >
          رجوع
        </button>
      </header>

      <Async state={state} loadingTitle="سجلّ التغييرات">
        {(data) =>
          data.entries.length ? (
            <Placard title="التغييرات" aside={`الأحدث أوّلًا · ${data.entries.length}`}>
              {data.entries.map((e) => (
                <div key={e.id} className="mb-2 border-b border-concrete/35 pb-2 last:border-0">
                  <Row
                    label={KIND_LABELS[e.kind] ?? e.kind}
                    value={timeFormatter.format(new Date(e.at))}
                  />
                  <p className="text-[13px] text-paint">{e.summary}</p>
                  <p className="text-[12px] text-muted">بواسطة {e.actor_name}</p>
                </div>
              ))}
            </Placard>
          ) : (
            <Empty title="التغييرات">لا تغييرات بعد.</Empty>
          )
        }
      </Async>
    </div>
  )
}
