import Placard, { Row } from '../components/Placard'
import { Async } from '../components/States'
import { api } from '../lib/api'
import { useAsync } from '../state/useAsync'

/*
  محطة التزوّد — و-٨ · FR-072.

  **شاشة طيّار لا مشرف**: كل عضو سرب يراها، بنفس منطق لوحات الصدارة —
  `@login_required` على الخادم لا `@admin_required` (`docs/slices/و-٨.md`).

  **كل رقم يصل محسوبًا**: اللترات تراكميّة من `GET /station`، ولا حساب هنا —
  نفس عقد `PilotDeck.jsx` (AGENTS.md ٥).
*/

const dayFormatter = new Intl.DateTimeFormat('ar-SA-u-ca-gregory-nu-latn', {
  day: 'numeric',
  month: 'long',
  timeZone: 'Asia/Riyadh',
})

const formatDay = (iso) => (iso ? dayFormatter.format(new Date(`${iso}T00:00:00Z`)) : null)

export default function Station({ onDone }) {
  const state = useAsync(() => api.station(), [])

  return (
    <div className="taxi-in mx-auto w-full max-w-[520px] px-4 pt-6 pb-10">
      <header className="mb-5 flex items-baseline gap-3">
        <h1 className="font-display text-[26px] leading-none">محطة التزوّد</h1>
        <span className="centerline" />
        <button
          type="button"
          onClick={onDone}
          className="min-h-[44px] shrink-0 px-2 text-[13px] text-muted"
        >
          رجوع
        </button>
      </header>

      <Async state={state} loadingTitle="محطة التزوّد">
        {(data) => <Body data={data} />}
      </Async>
    </div>
  )
}

function Body({ data }) {
  const { team, tank_capacity_l: capacity, recent } = data

  if (!team) {
    return (
      <Placard title="السرب">
        <p className="text-[14px] text-muted">لست في سرب حاليًّا. راجع المشرف.</p>
      </Placard>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <Placard title={team.name} aside="وقود السرب">
        <Row label="اللترات" value={<bdi dir="ltr">{team.litres}</bdi>} tone="taxi" />
        {capacity && (
          <Row label="سعة الخزّان" value={<bdi dir="ltr">{capacity}</bdi>} tone="muted" />
        )}
      </Placard>

      <Placard title="آخر التقييمات">
        {recent.length ? (
          recent.map((r, i) => (
            <div key={i} className="mb-2 border-b border-concrete/35 pb-2 last:border-0">
              <Row
                label={r.activity_name}
                value={<bdi dir="ltr">{r.litres}</bdi>}
                tone="taxi"
              />
              <p className="text-[12px] text-muted">
                {formatDay(r.occurred_on)} · <bdi dir="ltr">{r.total_pct}</bdi>٪
              </p>
            </div>
          ))
        ) : (
          <p className="py-2 text-[14px] text-muted">لا تقييمات بعد.</p>
        )}
      </Placard>
    </div>
  )
}
