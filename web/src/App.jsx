import { Failed, Loading } from './components/States'
import Login from './pages/Login'
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

  // 'checking': بدونها تومض شاشة الدخول لمن هو داخل أصلًا.
  if (status === 'checking') return <Shell><Loading title="جارٍ التحقّق" /></Shell>
  if (status === 'error') return <Shell><Failed error={error} onRetry={refresh} /></Shell>
  return status === 'in' ? <PilotDeck /> : <Login />
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
