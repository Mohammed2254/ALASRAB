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
import Notes from './screens/admin/Notes'
import ReadingQueue from './screens/admin/ReadingQueue'
import Report from './screens/admin/Report'
import TahdirQueue from './screens/admin/TahdirQueue'
import TahdirReport from './screens/admin/TahdirReport'
import Teams from './screens/admin/Teams'
import Thresholds from './screens/admin/Thresholds'
import AdminWeekPilot from './screens/admin/WeekPilot'
import Weights from './screens/admin/Weights'
import Boards from './screens/Boards'
import DailyQuestion from './screens/DailyQuestion'
import Deck from './screens/Deck'
import Formation from './screens/Formation'
import Login from './screens/Login'
import PilotShell from './screens/PilotShell'
import Readings from './screens/Readings'
import Station from './screens/Station'
import SubmitNote from './screens/SubmitNote'
import Tahdir from './screens/Tahdir'
import WeekPilot from './screens/WeekPilot'
import { AppStateProvider, useApp } from './state/AppState'

/**
 * الشاشات الخمس على شريط التبويب (و-١٥) — سجلٌّ لا سلسلة `if` (نفس نمط
 * `SCREENS` في البناء المرجعي `web/`، `HANDOFF.md` §٤): إضافة شاشة سطرٌ واحد.
 */
const PILOT_TABS: Partial<Record<ScreenKey, () => React.JSX.Element>> = {
  deck: Deck,
  readings: Readings,
  station: Station,
  formation: Formation,
  board: Boards,
}

/**
 * الشاشات الفرعية — طيّار (و-١٦) وإداريّ (و-١٧) معًا: كلاهما يُرسَم داخل
 * `Shell` البسيط بـ`Subback` خاصّته لا شريط تبويب، فسجلٌّ واحد لا سجلّان
 * (`و-١٧.md` §٢ قرار ٦؛ كان اسمه `PILOT_SUB_SCREENS` قبل أن يستوعب شاشات
 * المشرف). **حراسة الدخول الإداريّ بالبلاطة لا هنا** — البلاطات في
 * `Deck.tsx` مشروطة بالدور أصلًا، وحرَس المسار الحقيقيّ في الخادم
 * (`@admin_required`) لا في هذا السجلّ (`AGENTS.md` ٩، `NavBar.jsx` تعليق
 * مطابق في `web/`). الباقي من ٢٥ شاشة (٦ مشرف) في و-١٨.
 */
const SUB_SCREENS: Partial<Record<ScreenKey, () => React.JSX.Element>> = {
  tahdir: Tahdir,
  question: DailyQuestion,
  weekPilot: WeekPilot,
  note: SubmitNote,
  adminReport: Report,
  adminQueue: ReadingQueue,
  adminTahdirQueue: TahdirQueue,
  adminTahdirReport: TahdirReport,
  adminTeams: Teams,
  adminWeights: Weights,
  adminThresholds: Thresholds,
  adminNotes: Notes,
  adminWeekPilot: AdminWeekPilot,
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

  const TabScreen = PILOT_TABS[screen]
  if (TabScreen) {
    return (
      <PilotShell active={screen}>
        <TabScreen />
      </PilotShell>
    )
  }

  const SubScreen = SUB_SCREENS[screen]
  if (SubScreen) {
    return (
      <Shell>
        <SubScreen />
      </Shell>
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
