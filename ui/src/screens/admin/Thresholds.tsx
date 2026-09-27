import { useState } from 'react'

import { api, ApiError } from '../../api'
import type { ThresholdRowForm, ThresholdsPreview } from '../../api/types/rulesAdmin'
import { useAsync } from '../../state/useAsync'
import { Async } from '../../ui/Async'
import Button from '../../ui/Button'
import EmptyState from '../../ui/EmptyState'
import Placard from '../../ui/Placard'
import Prow from '../../ui/Prow'

/**
 * العتبات — `GET/POST /admin/thresholds*` (FR-082). **الرتبة لا تنخفض**
 * (و-٧ · ت-٢): الخادم يضمن ذلك، و`demoted` تصل فارغة دائمًا — الواجهة
 * تعرض ما وصل ولا تحسبه. **معاينة قبل حفظ إلزامية** — تغييرٌ يمسّ كل طالب
 * دفعة واحدة يستحقّ نظرة قبله؛ زرّ الحفظ معطَّل حتى تُشغَّل المعاينة.
 */
const rowInputClass = 'min-h-[44px] rounded-(--radius-sm) border border-(--color-border-strong) bg-(--color-bg-2) px-2 text-[14px] text-(--color-text)'

function Editor({ initial, onSaved }: { initial: ThresholdRowForm[]; onSaved: () => void }) {
  const [rows, setRows] = useState<ThresholdRowForm[]>(initial.map((r) => ({ ...r })))
  const [preview, setPreview] = useState<ThresholdsPreview | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const update = (i: number, field: keyof ThresholdRowForm, value: string) =>
    setRows((rs) => rs.map((r, idx) => (idx === i ? { ...r, [field]: value } : r)))

  async function runPreview() {
    setBusy(true)
    setError('')
    setPreview(null)
    try {
      setPreview(await api.admin.previewThresholds({ thresholds: rows }))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
    } finally {
      setBusy(false)
    }
  }

  async function save() {
    setBusy(true)
    setError('')
    try {
      await api.admin.saveThresholds({ thresholds: rows })
      setPreview(null)
      onSaved()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-3.5">
      <Placard title="السُّلّم">
        {rows.map((r, i) => (
          <div key={r.key} className="mb-3 border-b border-(--color-border) pb-3 last:border-none">
            <p className="mb-1.5 text-[13px] text-(--color-text-dim)">{r.key}</p>
            <div className="flex gap-2">
              <input
                aria-label={`اسم الرتبة ${r.key}`}
                value={r.name}
                onChange={(e) => update(i, 'name', e.target.value)}
                className={`${rowInputClass} min-w-0 flex-1`}
              />
              <input
                aria-label={`عتبة الساعات ${r.key}`}
                value={r.at_hours}
                onChange={(e) => update(i, 'at_hours', e.target.value)}
                className={`${rowInputClass} w-28`}
              />
            </div>
          </div>
        ))}
      </Placard>

      {preview ? (
        <Placard title="أثر التغيير" aside="قبل الحفظ">
          {preview.promoted.length ? (
            preview.promoted.map((p) => <Prow key={p.user_id} label={`طيار #${p.user_id}`} value="يرتفع" tone="accent" />)
          ) : (
            <EmptyState>لا أحد يرتفع بهذا التغيير.</EmptyState>
          )}
          <p className="mt-2 text-[12px] text-(--color-text-dim)">ولا أحد يتراجع أبدًا — الرتبة المكتسَبة محفوظة (و-٧).</p>
        </Placard>
      ) : null}

      {error ? (
        <p role="alert" className="text-[13px] text-(--color-red-text)">
          {error}
        </p>
      ) : null}

      <div className="flex gap-2">
        <Button variant="outline" disabled={busy} onClick={runPreview} className="flex-1">
          معاينة الأثر
        </Button>
        <Button disabled={busy || !preview} onClick={save} className="flex-1">
          {busy ? 'جارٍ الحفظ…' : 'حفظ'}
        </Button>
      </div>
    </div>
  )
}

export default function Thresholds() {
  const state = useAsync(() => api.admin.thresholds(), [])

  return (
    <div className="flex flex-col gap-3.5">
      <Async state={state} loadingTitle="العتبات">
        {(data) => (
          <Editor
            initial={data.thresholds.map((r) => ({ key: r.key, name: r.name, tier: String(r.tier), at_hours: r.at_hours }))}
            onSaved={state.reload}
          />
        )}
      </Async>
    </div>
  )
}
