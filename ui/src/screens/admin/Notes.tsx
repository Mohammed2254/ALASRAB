import { api } from '../../api'
import { useAsync } from '../../state/useAsync'
import { Async } from '../../ui/Async'
import EmptyState from '../../ui/EmptyState'
import Placard from '../../ui/Placard'

/**
 * **الصندوق الأسود** — `GET/PATCH /admin/notes*` (م-٥ · `SCOPE.md §٨` بند
 * ١٣: «الصندوق الأسود (ملاحظة مجهولة)»).
 *
 * الاسم صُحِّح في و-٢١: كان هذا الملفّ «الملاحظات» و`AuditLog.tsx` هو
 * «الصندوق الأسود» — مقلوبًا عن `SCOPE.md`.
 *
 * **بلا مصدر ولا قناة ردّ** — لا حقل يشير إلى مرسِل في العقد أصلًا (ث-١٢)،
 * والجهالة **بنية الجدول لا سياسة** (`NFR-04`). تعليمٌ كمقروءة فقط — لا حذف:
 * «ويجيني أشوفه، فقط» (قرار المستخدم).
 */
const dayFormatter = new Intl.DateTimeFormat('ar-SA-u-ca-gregory-nu-latn', {
  day: 'numeric',
  month: 'long',
  timeZone: 'Asia/Riyadh',
})
const formatDay = (iso: string) => dayFormatter.format(new Date(`${iso}T00:00:00Z`))

export default function Notes() {
  const state = useAsync(() => api.admin.notes(), [])

  async function markRead(id: number) {
    await api.admin.markNoteRead(id)
    state.reload()
  }

  return (
    <div className="flex flex-col gap-3.5">
      <Async state={state} loadingTitle="الملاحظات">
        {(data) =>
          data.notes.length === 0 ? (
            <Placard title="ملاحظات واردة">
              <EmptyState>لا ملاحظات بعد.</EmptyState>
            </Placard>
          ) : (
            <Placard title="ملاحظات واردة" aside={`${data.notes.length}`}>
              {data.notes.map((n) => (
                <div key={n.id} className="mb-3 border-b border-(--color-border) pb-3 last:mb-0 last:border-none">
                  <p className={`text-[14px] ${n.read_at ? 'text-(--color-text-dim)' : 'text-(--color-text)'}`}>{n.body}</p>
                  <div className="mt-2 flex items-center justify-between">
                    <span className="text-[12px] text-(--color-text-dim)">{formatDay(n.day)}</span>
                    {n.read_at ? (
                      <span className="text-[12px] text-(--color-text-dim)">مقروءة</span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => markRead(n.id)}
                        className="min-h-[44px] shrink-0 px-3 text-[13px] text-(--color-accent)"
                      >
                        تعليم كمقروءة
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </Placard>
          )
        }
      </Async>
    </div>
  )
}
