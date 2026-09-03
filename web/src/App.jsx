import { useState } from 'react'

import { Failed, Loading } from './components/States'
import AuditLog from './pages/admin/AuditLog'
import FuelActivities from './pages/admin/FuelActivities'
import FuelAssess from './pages/admin/FuelAssess'
import ReadingQueue from './pages/admin/ReadingQueue'
import Report from './pages/admin/Report'
import Teams from './pages/admin/Teams'
import Thresholds from './pages/admin/Thresholds'
import Weights from './pages/admin/Weights'
import Login from './pages/Login'
import MyReadings from './pages/MyReadings'
import PilotDeck from './pages/PilotDeck'
import Station from './pages/Station'
import { AppStateProvider, useApp } from './state/AppState'

/*
  حالة شاشة واحدة — **بلا موجّه مسارات**، قرارٌ مؤرَّخ أُعيد النظر فيه فعليًّا
  عند و-٩ كما وعد `docs/slices/و-٤.md`، لا مؤجَّلًا بصمت: لا دليل حاجة إلى
  عناوين تُشارَك أو تُحفَظ لهذه اللوحات الداخلية (`HANDOFF.md` §٤ يضع
  `react-router` ضمن «مرفوض عمدًا بلا دليل حاجة» — لم يظهر الدليل).

  **٩أ بدلًا منه:** سجلّ شاشات (`SCREENS`) لا سلسلة `if` متمدِّدة. أضف شاشة
  جديدة بسطر واحد هنا، لا فرعٍ جديد (`docs/slices/و-٩.md`).
*/
const SCREENS = {
  readings: MyReadings,
  queue: ReadingQueue,
  report: Report,
  weights: Weights,
  thresholds: Thresholds,
  teams: Teams,
  audit: AuditLog,
  station: Station,
  fuelActivities: FuelActivities,
  fuelAssess: FuelAssess,
}

function Gate() {
  const { status, error, refresh } = useApp()
  const [screen, setScreen] = useState('deck')

  if (status === 'checking') return <Shell><Loading title="جارٍ التحقّق" /></Shell>
  if (status === 'error') return <Shell><Failed error={error} onRetry={refresh} /></Shell>
  if (status !== 'in') return <Login />

  // 'deck' (الحالة الابتدائية) بلا مدخل في السجلّ عمدًا — البطاقة هي الشاشة
  // الافتراضية لا وجهة تُفتَح، فتُعرَض حين لا يطابق المفتاح شيئًا.
  const ActiveScreen = SCREENS[screen]
  if (ActiveScreen) return <ActiveScreen onDone={() => setScreen('deck')} />
  return <PilotDeck onNavigate={setScreen} />
}

function Shell({ children }) {
  return <div className="mx-auto w-full max-w-[520px] px-4 pt-6">{children}</div>
}

export default function App() {
  return (
    <AppStateProvider>
      <Gate />
    </AppStateProvider>
  )
}
