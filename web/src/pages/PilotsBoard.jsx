import Placard, { Row } from '../components/Placard'
import { Async } from '../components/States'
import { api } from '../lib/api'
import { useAsync } from '../state/useAsync'

/*
  صدارة الأفراد — و-٩ب · FR-050.

  **نافذة الأسبوع الحالي لا تراكميّة** — `hours` هنا مختلفة عمدًا عن
  `hours` في `PilotDeck.jsx` (الرصيد الكلّي). كلاهما يصل محسوبًا من الخادم؛
  لا حساب هنا (`docs/design/API.md` §٥).
*/

export default function PilotsBoard({ onDone }) {
  const state = useAsync(() => api.pilotsBoard(), [])

  return (
    <div className="taxi-in mx-auto w-full max-w-[520px] px-4 pt-6 pb-10">
      <header className="mb-5 flex items-baseline gap-3">
        <h1 className="font-display text-[26px] leading-none">صدارة الأفراد</h1>
        <span className="centerline" />
        <button
          type="button"
          onClick={onDone}
          className="min-h-[44px] shrink-0 px-2 text-[13px] text-muted"
        >
          رجوع
        </button>
      </header>

      <Async state={state} loadingTitle="صدارة الأفراد">
        {(data) => <Body pilots={data.pilots} />}
      </Async>
    </div>
  )
}

function Body({ pilots }) {
  if (!pilots.length) {
    return (
      <Placard title="هذا الأسبوع">
        <p className="py-2 text-[14px] text-muted">لا نشاط هذا الأسبوع بعد.</p>
      </Placard>
    )
  }

  return (
    <Placard title="هذا الأسبوع" aside={`${pilots.length} طيّارًا`}>
      {pilots.map((p, i) => (
        <Row
          key={i}
          label={`${i + 1}. ${p.full_name}`}
          value={<bdi dir="ltr">{p.hours}</bdi>}
          tone="taxi"
        />
      ))}
    </Placard>
  )
}
