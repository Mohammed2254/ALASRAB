import { useRef, useState, type FormEvent } from 'react'

import { api, ApiError } from '../api'
import { go } from '../nav/history'
import Button from '../ui/Button'
import PlaneIcon from '../ui/PlaneIcon'
import { flyAway } from '../motion/mo'
import Placard from '../ui/Placard'
import Subback from '../ui/Subback'

/**
 * ملاحظة مجهولة — `POST /notes` (FR-061). **بلا تاريخ إرسال ولا سجلّ يُعرض
 * هنا** — الملاحظة تختفي من نظر المرسِل فور إرسالها؛ عرض سجلّ بها كان
 * سيربط الهوية بمحتواها في ذهن القارئ نفسه (`DATABASE.md` §٣). ٢٠١ بلا
 * جسمٍ إطلاقًا — لا `id` يُعاد، فلا شيء يُحفَظ محليًّا بعد الإرسال.
 */
const NOTE_MAX = 280

export default function SubmitNote() {
  const [body, setBody] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [sent, setSent] = useState(false)
  // سقف ٢٨٠ حرفًا بعدّادٍ حيّ — كما في النموذج المعتمد.
  const planeRef = useRef<HTMLSpanElement>(null)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api.engagement.submitNote(body.trim())
      // الطائرة تنطلق **بعد** نجاح الإرسال لا قبله: حركةٌ تسبق التأكيد
      // تَعِد بما قد لا يقع. والوعد يُبقي المؤقّت في `motion/` لا هنا.
      await flyAway(planeRef.current)
      setBody('')
      setSent(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-3.5">
      <Subback label="الرئيسية" onClick={() => go('deck')} />
      <Placard title="بلا اسمك">
        {sent ? (
          <p className="py-2 text-[14px] text-(--color-accent)">أُرسلت. شكرًا لك.</p>
        ) : (
          <form onSubmit={onSubmit} className="flex flex-col gap-3">
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={5}
              maxLength={NOTE_MAX}
              placeholder="اكتب ما تريد…"
              className="w-full rounded-(--radius-sm) border border-(--color-border-strong) bg-(--color-bg-2) p-3 text-[16px] text-(--color-text)"
            />
            {error ? (
              <p role="alert" className="text-[13px] text-(--color-red-text)">
                {error}
              </p>
            ) : null}
            <div className="flex items-center justify-between gap-2">
              <span className="text-[12px] text-(--color-text-dim)">
                <bdi dir="ltr">{body.length}</bdi>/<bdi dir="ltr">{NOTE_MAX}</bdi>
              </span>
            </div>
            <Button type="submit" disabled={busy || !body.trim()} className="w-full">
              <span className="inline-flex items-center gap-2">
                إرسال
                <span ref={planeRef} className="inline-flex">
                  <PlaneIcon size={16} color="currentColor" />
                </span>
              </span>
            </Button>
          </form>
        )}
      </Placard>
    </div>
  )
}
