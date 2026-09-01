import { useState } from 'react'

import Placard, { Row } from '../../components/Placard'
import { Async } from '../../components/States'
import { api } from '../../lib/api'
import { useAsync } from '../../state/useAsync'

/*
  العتبات — و-٧ · FR-082.

  **الرتبة لا تنخفض** (و-٧ · ت-٢): الخادم يضمن أن أحدًا لا يتراجع بتغيير عتبة،
  و`demoted` تصل فارغة دائمًا — الواجهة تعرض ما وصل ولا تحسبه (AGENTS.md ٥).
  **معاينة قبل حفظ إلزامية هنا**: تغيير يمسّ كل طالب دفعة واحدة يستحقّ نظرة قبله.
*/

export default function Thresholds({ onDone }) {
  const state = useAsync(() => api.thresholds(), [])

  return (
    <div className="taxi-in mx-auto w-full max-w-[520px] px-4 pt-6 pb-10">
      <header className="mb-5 flex items-baseline gap-3">
        <h1 className="font-display text-[26px] leading-none">العتبات</h1>
        <span className="centerline" />
        <button
          type="button"
          onClick={onDone}
          className="min-h-[44px] shrink-0 px-2 text-[13px] text-muted"
        >
          رجوع
        </button>
      </header>

      <Async state={state} loadingTitle="العتبات">
        {(data) => <Editor initial={data.thresholds} onSaved={state.reload} />}
      </Async>
    </div>
  )
}

function Editor({ initial, onSaved }) {
  const [rows, setRows] = useState(initial.map((r) => ({ ...r })))
  const [preview, setPreview] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const update = (i, field, value) =>
    setRows((rs) => rs.map((r, idx) => (idx === i ? { ...r, [field]: value } : r)))

  const asPayload = () =>
    rows.map((r) => ({
      key: r.key,
      name: r.name,
      tier: Number(r.tier),
      at_hours: r.at_hours,
    }))

  async function runPreview() {
    setBusy(true)
    setError('')
    setPreview(null)
    try {
      setPreview(await api.previewThresholds(asPayload()))
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function save() {
    setBusy(true)
    setError('')
    try {
      await api.saveThresholds(asPayload())
      setPreview(null)
      onSaved()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Placard title="السُّلّم">
        {rows.map((r, i) => (
          <div key={r.key} className="mb-3 border-b border-concrete/35 pb-3 last:border-0">
            <p className="mb-1.5 text-[13px] text-muted">{r.key}</p>
            <div className="flex gap-2">
              <input
                aria-label={`اسم الرتبة ${r.key}`}
                value={r.name}
                onChange={(e) => update(i, 'name', e.target.value)}
                className="min-h-[44px] flex-1 border border-concrete/45 bg-taxiway px-2 text-[14px] text-paint"
              />
              <input
                aria-label={`عتبة الساعات ${r.key}`}
                value={r.at_hours}
                onChange={(e) => update(i, 'at_hours', e.target.value)}
                className="min-h-[44px] w-28 border border-concrete/45 bg-taxiway px-2 text-[14px] text-paint"
              />
            </div>
          </div>
        ))}
      </Placard>

      {preview && (
        <Placard title="أثر التغيير" aside="قبل الحفظ">
          {preview.promoted.length ? (
            preview.promoted.map((p) => (
              <Row
                key={p.user_id}
                label={`طيار #${p.user_id}`}
                value="يرتفع"
                tone="taxi"
              />
            ))
          ) : (
            <p className="py-2 text-[14px] text-muted">لا أحد يرتفع بهذا التغيير.</p>
          )}
          <p className="mt-2 text-[12px] text-muted">
            ولا أحد يتراجع أبدًا — الرتبة المكتسَبة محفوظة (و-٧).
          </p>
        </Placard>
      )}

      {error && (
        <p role="alert" className="text-[13px] text-hold">
          {error}
        </p>
      )}

      <div className="flex gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={runPreview}
          className="min-h-[48px] flex-1 border border-concrete/45 text-[15px] text-paint disabled:opacity-40"
        >
          معاينة الأثر
        </button>
        <button
          type="button"
          disabled={busy || !preview}
          onClick={save}
          className="min-h-[48px] flex-1 border border-taxi bg-taxi text-[15px] text-asphalt disabled:opacity-40"
        >
          {busy ? 'جارٍ الحفظ…' : 'حفظ'}
        </button>
      </div>
    </div>
  )
}
