import { useState } from 'react'

import { api, ApiError } from '../../api'
import type { RosterRow } from '../../api/types/roster'
import ErrorText from '../../ui/ErrorText'

/**
 * إجراءات الصفّ — ثلاثة أفعال كلّها لها أثرٌ لا يُرى فورًا، فكلٌّ منها
 * يُعرض بنصّ صريح لما سيقع لا بأيقونة.
 *
 * **وإعادة تعيين الرمز تعرض الرمز في مكانه**: كانت في شاشة التقرير وحدها
 * (و-١٧)، وهي صفةُ طالبٍ لا صفةُ تقرير.
 */
export default function StudentRowActions({ row, onChanged }: { row: RosterRow; onChanged: () => void }) {
  const [pin, setPin] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function run(action: () => Promise<void>) {
    setBusy(true)
    setError('')
    try {
      await action()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
    } finally {
      setBusy(false)
    }
  }

  const buttonClass =
    'min-h-[44px] shrink-0 rounded-(--radius-sm) border border-(--color-border-strong) px-3 text-[13px] text-(--color-text-dim) disabled:opacity-40'

  return (
    <div className="flex flex-col items-start gap-1.5">
      <div className="flex flex-wrap gap-1.5">
        <button
          type="button"
          disabled={busy}
          className={buttonClass}
          onClick={() =>
            run(async () => {
              setPin((await api.admin.resetPin(row.id)).pin)
            })
          }
        >
          رمز جديد
        </button>
        <button
          type="button"
          disabled={busy}
          className={buttonClass}
          onClick={() =>
            run(async () => {
              await api.admin.setStudentRole(row.id, row.role === 'admin' ? 'pilot' : 'admin')
              onChanged()
            })
          }
        >
          {row.role === 'admin' ? 'تنزيل إلى طيار' : 'ترقية إلى مشرف'}
        </button>
        <button
          type="button"
          disabled={busy}
          className={buttonClass}
          onClick={() =>
            run(async () => {
              await api.admin.setStudentActive(row.id, !row.is_active)
              onChanged()
            })
          }
        >
          {row.is_active ? 'تعطيل' : 'إعادة تفعيل'}
        </button>
      </div>

      {pin ? (
        <p className="text-[13px] text-(--color-accent)">
          الرمز الجديد <bdi dir="ltr" className="font-bold">{pin}</bdi> — لا يُعرض مرّة أخرى.
        </p>
      ) : null}
      {error ? <ErrorText spacing="">{error}</ErrorText> : null}
    </div>
  )
}
