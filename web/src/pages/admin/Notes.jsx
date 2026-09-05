import Placard, { Row } from '../../components/Placard'
import { Async } from '../../components/States'
import { api } from '../../lib/api'
import { useAsync } from '../../state/useAsync'

/*
  الملاحظات — و-٩د · م-٥.

  **بلا مصدر ولا قناة ردّ** — لا حقل يشير إلى مرسِل في العقد أصلًا (ث-١٢)،
  فلا شيء هنا يعرضه لو أُضيف بالخطأ. تعليمٌ كمقروءة فقط — لا حذف.
*/

const dayFormatter = new Intl.DateTimeFormat('ar-SA-u-ca-gregory-nu-latn', {
  day: 'numeric',
  month: 'long',
  timeZone: 'Asia/Riyadh',
})

const formatDay = (iso) => (iso ? dayFormatter.format(new Date(`${iso}T00:00:00Z`)) : null)

export default function Notes({ onDone }) {
  const state = useAsync(() => api.adminNotes(), [])

  return (
    <div className="taxi-in mx-auto w-full max-w-[520px] px-4 pt-6 pb-10">
      <header className="mb-5 flex items-baseline gap-3">
        <h1 className="font-display text-[26px] leading-none">الملاحظات</h1>
        <span className="centerline" />
        <button
          type="button"
          onClick={onDone}
          className="min-h-[44px] shrink-0 px-2 text-[13px] text-muted"
        >
          رجوع
        </button>
      </header>

      <Async state={state} loadingTitle="الملاحظات">
        {(data) => <List notes={data.notes} onChanged={state.reload} />}
      </Async>
    </div>
  )
}

function List({ notes, onChanged }) {
  if (!notes.length) {
    return (
      <Placard title="الوارد">
        <p className="py-2 text-[14px] text-muted">لا ملاحظات بعد.</p>
      </Placard>
    )
  }

  async function markRead(id) {
    await api.markNoteRead(id)
    onChanged()
  }

  return (
    <Placard title="الوارد" aside={`${notes.length}`}>
      {notes.map((n) => (
        <div key={n.id} className="mb-3 border-b border-concrete/35 pb-3 last:mb-0 last:border-0">
          <p className={`text-[14px] ${n.read_at ? 'text-muted' : 'text-paint'}`}>{n.body}</p>
          <div className="mt-2 flex items-center justify-between">
            <Row label="اليوم" value={formatDay(n.day)} tone="muted" />
            {n.read_at ? (
              <span className="text-[12px] text-muted">مقروءة</span>
            ) : (
              <button
                type="button"
                onClick={() => markRead(n.id)}
                className="min-h-[44px] shrink-0 px-3 text-[13px] text-taxi"
              >
                تعليم كمقروءة
              </button>
            )}
          </div>
        </div>
      ))}
    </Placard>
  )
}
