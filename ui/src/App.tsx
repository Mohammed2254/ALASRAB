/**
 * البوّابة والقشرة.
 *
 * **بوّابة الدخول ليست مسارًا** (ADR-008): تُعرَض فوق أيّ عنوان بلا لمس
 * السجلّ، فرابطٌ عميق يُفتح قبل الدخول ينجو ويُستأنف بعده. ولو كانت مسارًا
 * لاحتاج الطالب رجوعًا بعد الدخول ليصل ما أراد.
 */
import { useEffect } from 'react'

import { init, listen } from './nav/history'
import { useScreen } from './nav/useNavigation'
import type { ScreenKey } from './nav/routes'
import Boards from './screens/Boards'
import Deck from './screens/Deck'
import Formation from './screens/Formation'
import Login from './screens/Login'
import PilotShell from './screens/PilotShell'
import Readings from './screens/Readings'
import Station from './screens/Station'
import { AppStateProvider, useApp } from './state/AppState'

/**
 * الشاشات الخمس المبنيّة حتى الآن (و-١٥) — سجلٌّ لا سلسلة `if` (نفس نمط
 * `SCREENS` في البناء المرجعي `web/`، `HANDOFF.md` §٤): إضافة شاشة سطرٌ واحد.
 * الباقي من الـ٢١ مسارًا يبقى عنصرًا نائبًا حتى و-١٦..و-١٨.
 */
const PILOT_TABS: Partial<Record<ScreenKey, () => React.JSX.Element>> = {
  deck: Deck,
  readings: Readings,
  station: Station,
  formation: Formation,
  board: Boards,
}

function Gate() {
  const { status, error, refresh } = useApp()
  const screen = useScreen()

  useEffect(() => {
    init()
    return listen()
  }, [])

  if (status === 'checking') {
    return (
      <Shell>
        <p className="text-[14px] text-(--color-text-dim)">جارٍ التحقّق…</p>
      </Shell>
    )
  }

  if (status === 'error') {
    return (
      <Shell>
        <p role="alert" className="mb-4 text-[14px] text-(--color-red-text)">
          {error?.message ?? 'تعذّر التحقّق من الجلسة.'}
        </p>
        <button
          type="button"
          onClick={refresh}
          className="min-h-[44px] rounded-(--radius-sm) border border-(--color-border-strong) px-5 text-[14px]"
        >
          إعادة المحاولة
        </button>
      </Shell>
    )
  }

  if (status !== 'in') return <Login />

  const ScreenComponent = PILOT_TABS[screen]
  if (ScreenComponent) {
    return (
      <PilotShell active={screen}>
        <ScreenComponent />
      </PilotShell>
    )
  }

  return (
    <Shell>
      <p className="text-[14px] text-(--color-text-dim)">الشاشة: {screen}</p>
    </Shell>
  )
}

function Shell({ children }: { children: React.ReactNode }) {
  return <div className="mx-auto w-full max-w-[520px] px-5 pt-8 pb-12">{children}</div>
}

export default function App() {
  return (
    <AppStateProvider>
      <Gate />
    </AppStateProvider>
  )
}
