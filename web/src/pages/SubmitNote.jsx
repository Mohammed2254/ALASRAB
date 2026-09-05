import { useState } from 'react'

import Placard from '../components/Placard'
import { api } from '../lib/api'

/*
  إرسال ملاحظة مجهولة — و-٩د · FR-061.

  **بلا تاريخ إرسال ولا سجلّ يُعرض هنا** — الملاحظة تختفي من نظر المرسِل فور
  إرسالها؛ عرض سجلّ بها كان سيربط الهوية بمحتواها في ذهن القارئ نفسه، وهو
  ما تمنعه بنية الجدول أصلًا (`docs/design/DATABASE.md` §٣).
*/

export default function SubmitNote({ onDone }) {
  const [body, setBody] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [sent, setSent] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api.submitNote(body.trim())
      setBody('')
      setSent(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="taxi-in mx-auto w-full max-w-[520px] px-4 pt-6 pb-10">
      <header className="mb-5 flex items-baseline gap-3">
        <h1 className="font-display text-[26px] leading-none">أرسل ملاحظة</h1>
        <span className="centerline" />
        <button
          type="button"
          onClick={onDone}
          className="min-h-[44px] shrink-0 px-2 text-[13px] text-muted"
        >
          رجوع
        </button>
      </header>

      <Placard title="بلا اسمك">
        {sent ? (
          <p className="py-2 text-[14px] text-taxi">أُرسلت. شكرًا لك.</p>
        ) : (
          <form onSubmit={onSubmit} className="flex flex-col gap-3">
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={5}
              placeholder="اكتب ما تريد..."
              className="w-full border border-concrete/45 bg-transparent p-3 text-[14px] text-paint"
            />
            {error && <p className="text-[13px] text-hold">{error}</p>}
            <button
              type="submit"
              disabled={busy || !body.trim()}
              className="min-h-[44px] border border-taxi text-[14px] text-taxi disabled:opacity-50"
            >
              إرسال
            </button>
          </form>
        )}
      </Placard>
    </div>
  )
}
