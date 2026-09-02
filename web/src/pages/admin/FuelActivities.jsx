import { useState } from 'react'

import Placard, { Row } from '../../components/Placard'
import { Async, Empty } from '../../components/States'
import { api } from '../../lib/api'
import { useAsync } from '../../state/useAsync'

/*
  أنشطة الوقود وبنودها — و-٨ · بنية تحتية لـ FR-070.

  **إنشاءٌ جديد لا تعديل**: الخادم يرفض أوزانًا لا تجمع ١٠٠٪ بالضبط — ث-١٠أ،
  في الخدمة والقاعدة معًا. لا حساب مجموع هنا (AGENTS.md ٥).
*/

export default function FuelActivities({ onDone }) {
  const state = useAsync(() => api.fuelActivities(), [])

  return (
    <div className="taxi-in mx-auto w-full max-w-[520px] px-4 pt-6 pb-10">
      <header className="mb-5 flex items-baseline gap-3">
        <h1 className="font-display text-[26px] leading-none">أنشطة الوقود</h1>
        <span className="centerline" />
        <button
          type="button"
          onClick={onDone}
          className="min-h-[44px] shrink-0 px-2 text-[13px] text-muted"
        >
          رجوع
        </button>
      </header>

      <Async state={state} loadingTitle="الأنشطة">
        {(data) => <Body activities={data.activities} onCreated={state.reload} />}
      </Async>
    </div>
  )
}

function Body({ activities, onCreated }) {
  return (
    <div className="flex flex-col gap-4">
      {activities.length ? (
        <Placard title="الأنشطة القائمة">
          {activities.map((a) => (
            <div key={a.id} className="mb-2 border-b border-concrete/35 pb-2 last:border-0">
              <Row label={a.name} value={<bdi dir="ltr">{a.litres_full}</bdi>} tone="taxi" />
              {a.criteria.map((c) => (
                <Row key={c.id} label={c.name} value={`${c.weight_pct}٪`} tone="muted" />
              ))}
            </div>
          ))}
        </Placard>
      ) : (
        <Empty title="الأنشطة القائمة">لا أنشطة بعد.</Empty>
      )}
      <NewActivityForm onCreated={onCreated} />
    </div>
  )
}

function NewActivityForm({ onCreated }) {
  const [key, setKey] = useState('')
  const [name, setName] = useState('')
  const [litresFull, setLitresFull] = useState('')
  const [criteria, setCriteria] = useState([{ key: '', name: '', weight_pct: '' }])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const update = (i, field, value) =>
    setCriteria((rows) => rows.map((r, idx) => (idx === i ? { ...r, [field]: value } : r)))

  const ready =
    key.trim() && name.trim() && litresFull.trim() && criteria.every((c) => c.key.trim() && c.name.trim() && c.weight_pct.trim())

  async function submit() {
    setBusy(true)
    setError('')
    try {
      await api.createFuelActivity({
        key: key.trim(),
        name: name.trim(),
        litres_full: litresFull,
        criteria: criteria.map((c) => ({
          key: c.key.trim(),
          name: c.name.trim(),
          weight_pct: c.weight_pct,
        })),
      })
      setKey('')
      setName('')
      setLitresFull('')
      setCriteria([{ key: '', name: '', weight_pct: '' }])
      onCreated()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Placard title="نشاط جديد">
      <label htmlFor="fa_key" className="mb-1.5 block text-[13px]">
        المفتاح
      </label>
      <input
        id="fa_key"
        value={key}
        onChange={(e) => setKey(e.target.value)}
        className="mb-3 min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint"
      />
      <label htmlFor="fa_name" className="mb-1.5 block text-[13px]">
        الاسم
      </label>
      <input
        id="fa_name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        className="mb-3 min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint"
      />
      <label htmlFor="fa_litres" className="mb-1.5 block text-[13px]">
        السعة الكاملة (لتر)
      </label>
      <input
        id="fa_litres"
        value={litresFull}
        onChange={(e) => setLitresFull(e.target.value)}
        className="mb-4 min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint"
      />

      <p className="mb-2 text-[13px] text-muted">البنود</p>
      {criteria.map((c, i) => (
        <div key={i} className="mb-2 flex gap-2">
          <input
            aria-label="مفتاح البند"
            value={c.key}
            onChange={(e) => update(i, 'key', e.target.value)}
            className="min-h-[44px] w-1/3 border border-concrete/45 bg-taxiway px-2 text-[14px] text-paint"
          />
          <input
            aria-label="اسم البند"
            value={c.name}
            onChange={(e) => update(i, 'name', e.target.value)}
            className="min-h-[44px] w-1/3 border border-concrete/45 bg-taxiway px-2 text-[14px] text-paint"
          />
          <input
            aria-label="وزن البند"
            value={c.weight_pct}
            onChange={(e) => update(i, 'weight_pct', e.target.value)}
            className="min-h-[44px] w-1/3 border border-concrete/45 bg-taxiway px-2 text-[14px] text-paint"
          />
        </div>
      ))}
      <button
        type="button"
        onClick={() => setCriteria((rows) => [...rows, { key: '', name: '', weight_pct: '' }])}
        className="mb-4 min-h-[44px] w-full border border-concrete/45 text-[13px] text-muted"
      >
        + بند جديد
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
        {busy ? 'جارٍ الإنشاء…' : 'إنشاء نشاط'}
      </button>
    </Placard>
  )
}
