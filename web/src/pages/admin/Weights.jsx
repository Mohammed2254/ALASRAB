import { useState } from 'react'

import Placard, { Row } from '../../components/Placard'
import { Async, Empty } from '../../components/States'
import { api } from '../../lib/api'
import { useAsync } from '../../state/useAsync'

/*
  إصدارات الأوزان — و-٧ · FR-081.

  **إصدارٌ جديد لا تعديل** على القائم: الخادم يرفض تاريخ سريان لا يلي آخر
  إصدار، ويرفض إسقاط نشاط كان محتسَبًا — وكلاهما رسالة من الخادم تُعرض كما هي،
  لا فحصًا هنا (AGENTS.md ٥).
*/

const dayFormatter = new Intl.DateTimeFormat('ar-SA-u-ca-gregory-nu-latn', {
  day: 'numeric',
  month: 'long',
  year: 'numeric',
  timeZone: 'Asia/Riyadh',
})

const formatDay = (iso) => (iso ? dayFormatter.format(new Date(iso)) : null)

export default function Weights({ onDone }) {
  const state = useAsync(() => api.weights(), [])

  return (
    <div className="taxi-in mx-auto w-full max-w-[520px] px-4 pt-6 pb-10">
      <header className="mb-5 flex items-baseline gap-3">
        <h1 className="font-display text-[26px] leading-none">الأوزان</h1>
        <span className="centerline" />
        <button
          type="button"
          onClick={onDone}
          className="min-h-[44px] shrink-0 px-2 text-[13px] text-muted"
        >
          رجوع
        </button>
      </header>

      <Async state={state} loadingTitle="الأوزان">
        {(data) => <Body data={data} onSaved={state.reload} />}
      </Async>
    </div>
  )
}

function Body({ data, onSaved }) {
  const { current, history } = data

  return (
    <div className="flex flex-col gap-4">
      {current ? (
        <Placard title="الإصدار الساري" aside={formatDay(current.effective_from)}>
          {current.note ? <p className="mb-2 text-[13px] text-muted">{current.note}</p> : null}
          {current.weights.map((w) => (
            <Row
              key={w.activity_type}
              label={w.activity_type}
              value={<bdi dir="ltr">{w.hours_per_unit}</bdi>}
            />
          ))}
          {current.multipliers.map((m) => (
            <Row
              key={m.grade}
              label={`مضاعف: ${m.grade}`}
              value={<bdi dir="ltr">{m.multiplier}</bdi>}
              tone="muted"
            />
          ))}
        </Placard>
      ) : (
        <Empty title="الإصدار الساري">لا إصدار أوزان مهيّأ بعد.</Empty>
      )}

      {history.length ? (
        <Placard title="إصدارات سابقة">
          {history.map((v) => (
            <Row key={v.id} label={formatDay(v.effective_from)} value={v.note ?? '—'} tone="muted" />
          ))}
        </Placard>
      ) : null}

      <NewVersionForm seed={current} onSaved={onSaved} />
    </div>
  )
}

function NewVersionForm({ seed, onSaved }) {
  const [effectiveFrom, setEffectiveFrom] = useState('')
  const [note, setNote] = useState('')
  const [weights, setWeights] = useState(
    seed ? seed.weights.map((w) => ({ ...w })) : [{ activity_type: '', hours_per_unit: '' }]
  )
  const [multipliers, setMultipliers] = useState(seed ? seed.multipliers.map((m) => ({ ...m })) : [])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const updateWeight = (i, field, value) =>
    setWeights((rows) => rows.map((r, idx) => (idx === i ? { ...r, [field]: value } : r)))
  const updateMultiplier = (i, field, value) =>
    setMultipliers((rows) => rows.map((r, idx) => (idx === i ? { ...r, [field]: value } : r)))

  const ready = Boolean(effectiveFrom.trim()) && weights.every((w) => w.activity_type.trim() && w.hours_per_unit.trim())

  async function submit() {
    setBusy(true)
    setError('')
    try {
      await api.createWeightVersion({
        effective_from: effectiveFrom,
        note: note.trim() || null,
        weights: weights.map((w) => ({
          activity_type: w.activity_type.trim(),
          hours_per_unit: w.hours_per_unit,
        })),
        multipliers: multipliers
          .filter((m) => m.grade.trim())
          .map((m) => ({ grade: m.grade.trim(), multiplier: m.multiplier })),
      })
      setEffectiveFrom('')
      setNote('')
      onSaved()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Placard title="إصدار جديد">
      <label htmlFor="effective_from" className="mb-1.5 block text-[13px]">
        تاريخ السريان
      </label>
      <input
        id="effective_from"
        type="date"
        value={effectiveFrom}
        onChange={(e) => setEffectiveFrom(e.target.value)}
        className="mb-4 min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint"
      />

      <label htmlFor="note" className="mb-1.5 block text-[13px]">
        ملاحظة (اختياري)
      </label>
      <input
        id="note"
        value={note}
        onChange={(e) => setNote(e.target.value)}
        className="mb-4 min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint"
      />

      <p className="mb-2 text-[13px] text-muted">الأوزان</p>
      {weights.map((w, i) => (
        <div key={i} className="mb-2 flex gap-2">
          <input
            aria-label="النشاط"
            value={w.activity_type}
            onChange={(e) => updateWeight(i, 'activity_type', e.target.value)}
            className="min-h-[44px] w-1/2 border border-concrete/45 bg-taxiway px-2 text-[14px] text-paint"
          />
          <input
            aria-label="الساعة لكل وحدة"
            value={w.hours_per_unit}
            onChange={(e) => updateWeight(i, 'hours_per_unit', e.target.value)}
            className="min-h-[44px] w-1/2 border border-concrete/45 bg-taxiway px-2 text-[14px] text-paint"
          />
        </div>
      ))}
      <button
        type="button"
        onClick={() => setWeights((rows) => [...rows, { activity_type: '', hours_per_unit: '' }])}
        className="mb-4 min-h-[44px] w-full border border-concrete/45 text-[13px] text-muted"
      >
        + نشاط جديد
      </button>

      <p className="mb-2 text-[13px] text-muted">المضاعفات (اختياري)</p>
      {multipliers.map((m, i) => (
        <div key={i} className="mb-2 flex gap-2">
          <input
            aria-label="التقدير"
            value={m.grade}
            onChange={(e) => updateMultiplier(i, 'grade', e.target.value)}
            className="min-h-[44px] w-1/2 border border-concrete/45 bg-taxiway px-2 text-[14px] text-paint"
          />
          <input
            aria-label="المضاعف"
            value={m.multiplier}
            onChange={(e) => updateMultiplier(i, 'multiplier', e.target.value)}
            className="min-h-[44px] w-1/2 border border-concrete/45 bg-taxiway px-2 text-[14px] text-paint"
          />
        </div>
      ))}
      <button
        type="button"
        onClick={() => setMultipliers((rows) => [...rows, { grade: '', multiplier: '' }])}
        className="mb-4 min-h-[44px] w-full border border-concrete/45 text-[13px] text-muted"
      >
        + مضاعف جديد
      </button>

      {error && (
        <p role="alert" className="mb-3 text-[13px] text-hold">
          {error}
        </p>
      )}

      <button
        type="button"
        disabled={busy || !ready}
        onClick={submit}
        className="min-h-[48px] w-full border border-taxi bg-taxi text-[16px] text-asphalt disabled:opacity-40"
      >
        {busy ? 'جارٍ الحفظ…' : 'حفظ إصدار جديد'}
      </button>
    </Placard>
  )
}
