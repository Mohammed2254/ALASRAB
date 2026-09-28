import { useState } from 'react'

import { api, ApiError } from '../../api'
import { fmtDecimal } from '../../api/format'
import type { CurrentWeightVersion, MultiplierRowForm, WeightRowForm } from '../../api/types/rulesAdmin'
import { useAsync } from '../../state/useAsync'
import { Async } from '../../ui/Async'
import Button from '../../ui/Button'
import EmptyState from '../../ui/EmptyState'
import Field from '../../ui/Field'
import Placard from '../../ui/Placard'
import Prow from '../../ui/Prow'

/**
 * إصدارات الأوزان — `GET/POST /admin/weights` (FR-081). **إصدارٌ جديد لا
 * تعديل** على القائم: الخادم يرفض تاريخ سريان لا يلي آخر إصدار، ورسالته
 * تُعرض كما هي (`AGENTS.md` ٥).
 */
const dayFormatter = new Intl.DateTimeFormat('ar-SA-u-ca-gregory-nu-latn', {
  day: 'numeric',
  month: 'long',
  year: 'numeric',
  timeZone: 'Asia/Riyadh',
})
const formatDay = (iso: string) => dayFormatter.format(new Date(iso))
// `min-w-0` ضروريّ لا زخرفة: بلا هذا يرفض المُدخَل الانكماش تحت عرضه
// الجوهريّ داخل `flex` (`min-width:auto` الافتراضيّ)، فيفيض عرض الصفّ عن
// الشاشة — عيبٌ حقيقيّ ضربه القياس الحيّ على `Thresholds.tsx` المطابقة.
const rowInputClass = 'min-h-[44px] w-1/2 min-w-0 rounded-(--radius-sm) border border-(--color-border-strong) bg-(--color-bg-2) px-2 text-[14px] text-(--color-text)'
const fieldClass = 'min-h-[48px] w-full rounded-(--radius-sm) border border-(--color-border-strong) bg-(--color-bg-2) px-3 text-[16px] text-(--color-text)'

function NewVersionForm({ seed, onSaved }: { seed: CurrentWeightVersion | null; onSaved: () => void }) {
  const [effectiveFrom, setEffectiveFrom] = useState('')
  const [note, setNote] = useState('')
  const [weights, setWeights] = useState<WeightRowForm[]>(
    seed ? seed.weights.map((w) => ({ ...w })) : [{ activity_type: '', hours_per_unit: '' }]
  )
  const [multipliers, setMultipliers] = useState<MultiplierRowForm[]>(seed ? seed.multipliers.map((m) => ({ ...m })) : [])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const updateWeight = (i: number, field: keyof WeightRowForm, value: string) =>
    setWeights((rows) => rows.map((r, idx) => (idx === i ? { ...r, [field]: value } : r)))
  const updateMultiplier = (i: number, field: keyof MultiplierRowForm, value: string) =>
    setMultipliers((rows) => rows.map((r, idx) => (idx === i ? { ...r, [field]: value } : r)))

  const ready = Boolean(effectiveFrom.trim()) && weights.every((w) => w.activity_type.trim() && w.hours_per_unit.trim())

  async function submit() {
    setBusy(true)
    setError('')
    try {
      await api.admin.createWeightVersion({
        effective_from: effectiveFrom,
        note: note.trim() || null,
        weights: weights.map((w) => ({ activity_type: w.activity_type.trim(), hours_per_unit: w.hours_per_unit })),
        multipliers: multipliers.filter((m) => m.grade.trim()).map((m) => ({ grade: m.grade.trim(), multiplier: m.multiplier })),
      })
      setEffectiveFrom('')
      setNote('')
      onSaved()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Placard title="إصدار جديد">
      <Field label="تاريخ السريان" htmlFor="effective_from">
        <input id="effective_from" type="date" value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.target.value)} className={fieldClass} />
      </Field>
      <Field label="ملاحظة (اختياري)" htmlFor="note">
        <input id="note" value={note} onChange={(e) => setNote(e.target.value)} className={fieldClass} />
      </Field>

      <p className="mb-2 text-[13px] text-(--color-text-dim)">الأوزان</p>
      {weights.map((w, i) => (
        <div key={i} className="mb-2 flex gap-2">
          <input aria-label="النشاط" value={w.activity_type} onChange={(e) => updateWeight(i, 'activity_type', e.target.value)} className={rowInputClass} />
          <input aria-label="الساعة لكل وحدة" value={w.hours_per_unit} onChange={(e) => updateWeight(i, 'hours_per_unit', e.target.value)} className={rowInputClass} />
        </div>
      ))}
      <button
        type="button"
        onClick={() => setWeights((rows) => [...rows, { activity_type: '', hours_per_unit: '' }])}
        className="mb-4 min-h-[44px] w-full rounded-(--radius-sm) border border-(--color-border-strong) text-[13px] text-(--color-text-dim)"
      >
        + نشاط جديد
      </button>

      <p className="mb-2 text-[13px] text-(--color-text-dim)">المضاعفات (اختياري)</p>
      {multipliers.map((m, i) => (
        <div key={i} className="mb-2 flex gap-2">
          <input aria-label="التقدير" value={m.grade} onChange={(e) => updateMultiplier(i, 'grade', e.target.value)} className={rowInputClass} />
          <input aria-label="المضاعف" value={m.multiplier} onChange={(e) => updateMultiplier(i, 'multiplier', e.target.value)} className={rowInputClass} />
        </div>
      ))}
      <button
        type="button"
        onClick={() => setMultipliers((rows) => [...rows, { grade: '', multiplier: '' }])}
        className="mb-4 min-h-[44px] w-full rounded-(--radius-sm) border border-(--color-border-strong) text-[13px] text-(--color-text-dim)"
      >
        + مضاعف جديد
      </button>

      {error ? (
        <p role="alert" className="mb-3 text-[13px] text-(--color-red-text)">
          {error}
        </p>
      ) : null}

      <Button disabled={busy || !ready} onClick={submit} className="w-full">
        {busy ? 'جارٍ الحفظ…' : 'حفظ إصدار جديد'}
      </Button>
    </Placard>
  )
}

export default function Weights() {
  const state = useAsync(() => api.admin.weights(), [])

  return (
    <div className="flex flex-col gap-3.5">
      <Async state={state} loadingTitle="الأوزان">
        {(data) => (
          <div className="flex flex-col gap-3.5">
            {data.current ? (
              <Placard title="أوزان الاحتساب" aside={formatDay(data.current.effective_from)}>
                {data.current.note ? <p className="mb-2 text-[13px] text-(--color-text-dim)">{data.current.note}</p> : null}
                {data.current.weights.map((w) => (
                  <Prow key={w.activity_type} label={w.activity_type} value={<bdi dir="ltr">{fmtDecimal(w.hours_per_unit)}</bdi>} />
                ))}
                {data.current.multipliers.map((m) => (
                  <Prow key={m.grade} label={`مضاعف: ${m.grade}`} value={<bdi dir="ltr">{fmtDecimal(m.multiplier)}</bdi>} />
                ))}
              </Placard>
            ) : (
              <Placard title="أوزان الاحتساب">
                <EmptyState>لا إصدار أوزان مهيّأ بعد.</EmptyState>
              </Placard>
            )}

            {data.history.length ? (
              <Placard title="إصدارات سابقة">
                {data.history.map((v) => (
                  // `WeightVersionIdSchema` لا يحمل `note` (`id`/`effective_from`
                  // فقط) — فلا شيء آخر يُعرض هنا، خلافًا لظنّ النموذج المعتمد.
                  <Prow key={v.id} label={formatDay(v.effective_from)} value="—" />
                ))}
              </Placard>
            ) : null}

            <NewVersionForm seed={data.current} onSaved={state.reload} />
          </div>
        )}
      </Async>
    </div>
  )
}
