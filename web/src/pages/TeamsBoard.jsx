import Placard, { Row } from '../components/Placard'
import { Async } from '../components/States'
import { api } from '../lib/api'
import { useAsync } from '../state/useAsync'

/*
  صدارة الأسراب — و-٩ب · FR-051 · FR-052.

  **بالمعدّل لا بالمجموع** — يصل `avg_hours` محسوبًا كذلك، فلا قسمة هنا.
  **فكّ التعادل بـ`code`**: الرمز يُعرض دائمًا بجانب الاسم — هذا هو معنى
  «معلَن في الواجهة» (`docs/design/API.md` §٥).
*/

export default function TeamsBoard({ onDone }) {
  const state = useAsync(() => api.teamsBoard(), [])

  return (
    <div className="taxi-in mx-auto w-full max-w-[520px] px-4 pt-6 pb-10">
      <header className="mb-5 flex items-baseline gap-3">
        <h1 className="font-display text-[26px] leading-none">صدارة الأسراب</h1>
        <span className="centerline" />
        <button
          type="button"
          onClick={onDone}
          className="min-h-[44px] shrink-0 px-2 text-[13px] text-muted"
        >
          رجوع
        </button>
      </header>

      <Async state={state} loadingTitle="صدارة الأسراب">
        {(data) => <Body teams={data.teams} />}
      </Async>
    </div>
  )
}

function Body({ teams }) {
  if (!teams.length) {
    return (
      <Placard title="هذا الأسبوع">
        <p className="py-2 text-[14px] text-muted">لا أسراب نشطة بعد.</p>
      </Placard>
    )
  }

  return (
    <Placard title="هذا الأسبوع — بالمعدّل" aside={`${teams.length} سربًا`}>
      {teams.map((t, i) => (
        <div key={i} className="mb-2 border-b border-concrete/35 pb-2 last:border-0">
          <Row
            label={`${i + 1}. ${t.team} (${t.code})`}
            value={<bdi dir="ltr">{t.avg_hours}</bdi>}
            tone="taxi"
          />
          <p className="text-[12px] text-muted">
            {t.members} أعضاء · {t.readiness.flying} طائر · {t.readiness.grounded} أرضي
          </p>
        </div>
      ))}
    </Placard>
  )
}
