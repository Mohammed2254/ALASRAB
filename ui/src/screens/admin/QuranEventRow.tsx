import { useState } from 'react'

import { api, ApiError } from '../../api'
import { fmtDecimal } from '../../api/format'
import type { QuranEventRow } from '../../api/types/quran'
import Button from '../../ui/Button'
import Field, { fieldClass } from '../../ui/Field'
import Prow from '../../ui/Prow'
import ErrorText from '../../ui/ErrorText'


/**
 * صفّ حدثٍ في سجلّ الطالب — **تعديل وحذف كما في النموذج، وADR-004 محفوظ.**
 *
 * التعارض ظاهريّ لا جوهريّ: الدفتر لا يُعدَّل ولا يُحذف منه، والمشرف يريد
 * تصحيح رقمٍ لا محوَ تاريخ. فـ«حذف» = حدثٌ معاكس، و«تعديل» = معاكسٌ + بديل
 * **في معاملةٍ واحدة** على الخادم. ويبقى الأثر كاملًا: أصلٌ وعكسٌ وبديل.
 */
type Mode = 'idle' | 'delete' | 'amend'

export default function EventRow({ event, onChanged }: { event: QuranEventRow; onChanged: () => void }) {
  const [mode, setMode] = useState<Mode>('idle')
  const [reason, setReason] = useState('')
  const [form, setForm] = useState({ occurred_on: '', activity_type: '', quantity: '', mastery: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  function close() {
    setMode('idle')
    setReason('')
    setError('')
  }

  async function run(action: () => Promise<unknown>) {
    setBusy(true)
    setError('')
    try {
      await action()
      close()
      onChanged()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
    } finally {
      setBusy(false)
    }
  }

  const amendReady =
    reason.trim() && form.occurred_on && form.activity_type.trim() && form.quantity.trim()

  return (
    <div className="mb-2 border-b border-(--color-border) pb-2 last:border-none">
      <Prow label={event.kind} value={<bdi dir="ltr">{fmtDecimal(event.delta)}</bdi>} />
      {event.reason ? <p className="text-[12px] text-(--color-text-dim)">{event.reason}</p> : null}

      {mode === 'idle' ? (
        <div className="mt-1 flex gap-2">
          <button
            type="button"
            onClick={() => setMode('amend')}
            className="min-h-[44px] flex-1 rounded-(--radius-sm) border border-(--color-border-strong) text-[13px] text-(--color-text-dim)"
          >
            تعديل
          </button>
          <button
            type="button"
            onClick={() => setMode('delete')}
            className="min-h-[44px] flex-1 rounded-(--radius-sm) border border-(--color-red) text-[13px] text-(--color-red-text)"
          >
            حذف
          </button>
        </div>
      ) : null}

      {mode !== 'idle' ? (
        <div className="mt-2">
          <p className="mb-2 text-[12px] text-(--color-text-dim)">
            {mode === 'delete'
              ? 'لا يُحذف من الدفتر — يُكتب حدثٌ معاكس يُلغي أثره، ويبقى الأصل مرئيًّا.'
              : 'لا يُعدَّل الأصل — يُعكَس ويُضاف بديلٌ بالقيم أدناه، في عمليةٍ واحدة.'}
          </p>

          {mode === 'amend' ? (
            <>
              <Field label="تاريخ الوقوع" htmlFor={`am_day_${event.id}`}>
                <input
                  id={`am_day_${event.id}`}
                  type="date"
                  value={form.occurred_on}
                  onChange={(e) => setForm((f) => ({ ...f, occurred_on: e.target.value }))}
                  className={fieldClass}
                />
              </Field>
              <Field label="النشاط" htmlFor={`am_act_${event.id}`}>
                <input
                  id={`am_act_${event.id}`}
                  value={form.activity_type}
                  onChange={(e) => setForm((f) => ({ ...f, activity_type: e.target.value }))}
                  className={fieldClass}
                />
              </Field>
              <Field label="الكمّية" htmlFor={`am_qty_${event.id}`}>
                <input
                  id={`am_qty_${event.id}`}
                  type="number"
                  inputMode="decimal"
                  value={form.quantity}
                  onChange={(e) => setForm((f) => ({ ...f, quantity: e.target.value }))}
                  className={fieldClass}
                />
              </Field>
              <Field label="التقدير — اختياريّ" htmlFor={`am_mas_${event.id}`}>
                <input
                  id={`am_mas_${event.id}`}
                  value={form.mastery}
                  onChange={(e) => setForm((f) => ({ ...f, mastery: e.target.value }))}
                  className={fieldClass}
                />
              </Field>
            </>
          ) : null}

          <Field label="السبب — إلزاميّ" htmlFor={`qe_reason_${event.id}`}>
            <input
              id={`qe_reason_${event.id}`}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className={fieldClass}
            />
          </Field>

          {error ? <ErrorText spacing="mt-1">{error}</ErrorText> : null}

          <div className="mt-2 flex gap-2">
            <Button
              variant="danger"
              disabled={busy || (mode === 'delete' ? !reason.trim() : !amendReady)}
              onClick={() =>
                run(() =>
                  mode === 'delete'
                    ? api.admin.reverseEvent(event.id, reason)
                    : api.admin.amendEvent(event.id, { ...form, reason })
                )
              }
              className="flex-1"
            >
              {mode === 'delete' ? 'تأكيد الحذف' : 'تأكيد التعديل'}
            </Button>
            <Button variant="outline" onClick={close} className="min-w-[80px]">
              إلغاء
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  )
}

