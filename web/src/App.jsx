import { useState } from 'react'

import { Failed, Loading } from './components/States'
import AuditLog from './pages/admin/AuditLog'
import ReadingQueue from './pages/admin/ReadingQueue'
import Report from './pages/admin/Report'
import Teams from './pages/admin/Teams'
import Thresholds from './pages/admin/Thresholds'
import Weights from './pages/admin/Weights'
import Login from './pages/Login'
import MyReadings from './pages/MyReadings'
import PilotDeck from './pages/PilotDeck'
import { AppStateProvider, useApp } from './state/AppState'

/*
  شاشتان تحكمهما حالة الجلسة — **بلا موجّه مسارات**.

  التبديل هنا ليس تنقّلًا بل بوّابة مصادقة: الدخول ليس عنوانًا يُزار بل الحالة
  التي يراها من ليس داخلًا. وإضافة `react-router` لشاشتين تعني اعتمادية وتحميلًا
  ومفهومًا زائدًا بلا مشكلة يحلّها اليوم. يُضاف حين تصير الوجهات وجهات.
*/
function Gate() {
  const { status, error, refresh } = useApp()
  /*
    ثلاث شاشات بحالة واحدة — **وما زال بلا موجّه مسارات.**

    التبديل هنا بوّابة مصادقة ثم عرضٌ داخليّ، لا تنقّلٌ بعناوين. والموجّه يُضاف
    في و-٩ حين تصير الوجهات وجهات لها روابط تُشارَك وتُحفَظ.
  */
  const [screen, setScreen] = useState('deck')

  if (status === 'checking') return <Shell><Loading title="جارٍ التحقّق" /></Shell>
  if (status === 'error') return <Shell><Failed error={error} onRetry={refresh} /></Shell>
  if (status !== 'in') return <Login />

  const back = () => setScreen('deck')
  if (screen === 'readings') return <MyReadings onDone={back} />
  if (screen === 'queue') return <ReadingQueue onDone={back} />
  if (screen === 'report') return <Report onDone={back} />
  if (screen === 'weights') return <Weights onDone={back} />
  if (screen === 'thresholds') return <Thresholds onDone={back} />
  if (screen === 'teams') return <Teams onDone={back} />
  if (screen === 'audit') return <AuditLog onDone={back} />
  return (
    <PilotDeck
      onOpenReadings={() => setScreen('readings')}
      onOpenQueue={() => setScreen('queue')}
      onOpenReport={() => setScreen('report')}
      onOpenWeights={() => setScreen('weights')}
      onOpenThresholds={() => setScreen('thresholds')}
      onOpenTeams={() => setScreen('teams')}
      onOpenAudit={() => setScreen('audit')}
    />
  )
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
