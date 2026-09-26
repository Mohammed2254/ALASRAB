import { useState } from 'react'

import { api, ApiError } from '../../api'
import { fmtDecimal } from '../../api/format'
import type { CriterionRowForm } from '../../api/types/fuel'
import { go } from '../../nav/history'
import { useAsync } from '../../state/useAsync'
import { Async } from '../../ui/Async'
import Button from '../../ui/Button'
import EmptyState from '../../ui/EmptyState'
import Field from '../../ui/Field'
import Placard from '../../ui/Placard'
import Prow from '../../ui/Prow'
import Subback from '../../ui/Subback'

/**
 * أنشطة الوقود وبنودها — `GET/POST /admin/fuel/activities` (بنية تحتية
 * لـFR-070). **إنشاءٌ جديد لا تعديل**: الخادم يرفض بنودًا لا تجمع ١٠٠٪
 * بالضبط (ث-١٠أ) — لا حساب مجموع هنا (`AGENTS.md` ٥).
 */
const fieldClass = 'min-h-[48px] w-full rounded-(--radius-sm) border border-(--color-border-strong) bg-(--color-bg-2) px-3 text-[16px] text-(--color-text)'
const rowInputClass = 'min-h-[44px] w-1/3 min-w-0 rounded-(--radius-sm) border border-(--color-border-strong) bg-(--color-bg-2) px-2 text-[14px] text-(--color-text)'

function NewActivityForm({ onCreated }: { onCreated: () => void }) {
  const [key, setKey] = useState('')
  const [name, setName] = useState('')
  const [litresFull, setLitresFull] = useState('')
  const [criteria, setCriteria] = useState<CriterionRowForm[]>([{ key: '', name: '', weight_pct: '' }])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const update = (i: number, field: keyof CriterionRowForm, value: string) =>
    setCriteria((rows) => rows.map((r, idx) => (idx === i ? { ...r, [field]: value } : r)))

  const ready =
    key.trim() && name.trim() && litresFull.trim() && criteria.every((c) => c.key.trim() && c.name.trim() && c.weight_pct.trim())

  async function submit() {
    setBusy(true)
    setError('')
    try {
      await api.admin.createFuelActivity({
        key: key.trim(),
        name: name.trim(),
        litres_full: litresFull,
        criteria: criteria.map((c) => ({ key: c.key.trim(), name: c.name.trim(), weight_pct: c.weight_pct })),
      })
      setKey('')
      setName('')
      setLitresFull('')
      setCriteria([{ key: '', name: '', weight_pct: '' }])
      onCreated()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Placard title="نشاط جديد">
      <Field label="المفتاح" htmlFor="fa_key">
        <input id="fa_key" value={key} onChange={(e) => setKey(e.target.value)} className={fieldClass} />
      </Field>
      <Field label="الاسم" htmlFor="fa_name">
        <input id="fa_name" value={name} onChange={(e) => setName(e.target.value)} className={fieldClass} />
      </Field>
      <Field label="السعة الكاملة (لتر)" htmlFor="fa_litres">
        <input id="fa_litres" value={litresFull} onChange={(e) => setLitresFull(e.target.value)} className={fieldClass} />
      </Field>

      <p className="mb-2 text-[13px] text-(--color-text-dim)">البنود</p>
      {criteria.map((c, i) => (
        <div key={i} className="mb-2 flex gap-2">
          <input aria-label="مفتاح البند" value={c.key} onChange={(e) => update(i, 'key', e.target.value)} className={rowInputClass} />
          <input aria-label="اسم البند" value={c.name} onChange={(e) => update(i, 'name', e.target.value)} className={rowInputClass} />
          <input aria-label="وزن البند" value={c.weight_pct} onChange={(e) => update(i, 'weight_pct', e.target.value)} className={rowInputClass} />
        </div>
      ))}
      <button
        type="button"
        onClick={() => setCriteria((rows) => [...rows, { key: '', name: '', weight_pct: '' }])}
        className="mb-4 min-h-[44px] w-full rounded-(--radius-sm) border border-(--color-border-strong) text-[13px] text-(--color-text-dim)"
      >
        + بند جديد
      </button>

      {error ? (
        <p role="alert" className="mb-3 text-[13px] text-(--color-red-text)">
          {error}
        </p>
      ) : null}

      <Button disabled={busy || !ready} onClick={submit} className="w-full">
        {busy ? 'جارٍ الإنشاء…' : 'إنشاء نشاط'}
      </Button>
    </Placard>
  )
}

export default function FuelActivities() {
  const state = useAsync(() => api.admin.fuelActivities(), [])

  return (
    <div className="flex flex-col gap-3.5">
      <Subback label="الرئيسية" onClick={() => go('deck')} />
      <Async state={state} loadingTitle="الأنشطة">
        {(data) => (
          <div className="flex flex-col gap-3.5">
            {data.activities.length ? (
              <Placard title="الأنشطة القائمة">
                {data.activities.map((a) => (
                  <div key={a.id} className="mb-2 border-b border-(--color-border) pb-2 last:border-none">
                    <Prow label={a.name} value={<bdi dir="ltr">{fmtDecimal(a.litres_full)}</bdi>} tone="accent" />
                    {a.criteria.map((c) => (
                      <Prow key={c.id} label={c.name} value={`${fmtDecimal(c.weight_pct)}٪`} />
                    ))}
                  </div>
                ))}
              </Placard>
            ) : (
              <Placard title="الأنشطة القائمة">
                <EmptyState>لا أنشطة بعد.</EmptyState>
              </Placard>
            )}
            <NewActivityForm onCreated={state.reload} />
          </div>
        )}
      </Async>
    </div>
  )
}
