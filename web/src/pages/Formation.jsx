import { useState } from 'react'

import Placard from '../components/Placard'
import { Async } from '../components/States'
import { api } from '../lib/api'
import { useAsync } from '../state/useAsync'

/*
  مشهد التشكيل — و-٩ب · FR-053.

  **`size_pct` يصل جاهزًا للعرض** — لا قسمة ولا ضرب هنا، نفس نمط
  `next_rank.progress_pct` في `PilotDeck.jsx` تمامًا (`check-no-domain-logic.mjs`).

  **محكوم بف-١**: `scope=team` أسماء كاملة شاملة الساقطين، `scope=general`
  بلا اسم للساقط (`name: null` من الخادم — `a.name ?? 'طيّار'` هنا عرضٌ لا قرار).
*/

export default function Formation({ onDone }) {
  const [scope, setScope] = useState('team')
  const state = useAsync(() => api.formation(scope), [scope])

  return (
    <div className="taxi-in mx-auto w-full max-w-[520px] px-4 pt-6 pb-10">
      <header className="mb-1 flex items-baseline gap-3">
        <h1 className="font-display text-[26px] leading-none">مشهد التشكيل</h1>
        <span className="centerline" />
        <button
          type="button"
          onClick={onDone}
          className="min-h-[44px] shrink-0 px-2 text-[13px] text-muted"
        >
          رجوع
        </button>
      </header>
      <p className="mb-5 text-[13px] text-muted">
        طول شريط كل طيّار يمثّل ساعات طيرانه — كلّما طال الشريط، زادت ساعاته.
      </p>

      <div className="mb-4 flex gap-2">
        <button
          type="button"
          onClick={() => setScope('team')}
          className={`min-h-[44px] flex-1 border text-[14px] ${scope === 'team' ? 'border-taxi text-taxi' : 'border-concrete/45 text-muted'}`}
        >
          سربي
        </button>
        <button
          type="button"
          onClick={() => setScope('general')}
          className={`min-h-[44px] flex-1 border text-[14px] ${scope === 'general' ? 'border-taxi text-taxi' : 'border-concrete/45 text-muted'}`}
        >
          عامّ
        </button>
      </div>

      <Async state={state} loadingTitle="مشهد التشكيل">
        {(data) => <Body aircraft={data.aircraft} />}
      </Async>
    </div>
  )
}

function Body({ aircraft }) {
  if (!aircraft.length) {
    return (
      <Placard title="التشكيل">
        <p className="py-2 text-[14px] text-muted">لا طيّارين في هذا المشهد بعد.</p>
      </Placard>
    )
  }

  return (
    <Placard title="التشكيل">
      {aircraft.map((a, i) => (
        <div key={i} className="mb-3 last:mb-0">
          <div className="mb-1 flex items-baseline justify-between gap-3">
            <span className={`text-[14px] ${a.grounded ? 'text-hold' : 'text-paint'}`}>
              {a.name ?? 'طيّار'}
              {a.grounded && ' · أرضي'}
            </span>
            <bdi dir="ltr" className="shrink-0 text-[13px] text-muted">
              {a.size}
            </bdi>
          </div>
          <div className="h-2 w-full bg-concrete/20">
            <div
              className={`h-full ${a.grounded ? 'bg-hold' : 'bg-taxi'}`}
              style={{ width: `${a.size_pct}%` }}
            />
          </div>
        </div>
      ))}
    </Placard>
  )
}
