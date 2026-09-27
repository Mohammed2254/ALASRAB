/**
 * البوّابة والقشرة.
 *
 * **بوّابة الدخول ليست مسارًا** (ADR-008): تُعرَض فوق أيّ عنوان بلا لمس
 * السجلّ، فرابطٌ عميق يُفتح قبل الدخول ينجو ويُستأنف بعده. ولو كانت مسارًا
 * لاحتاج الطالب رجوعًا بعد الدخول ليصل ما أراد.
 *
 * **وهذا الملفّ تحكّمٌ لا جدول** (و-٢٠): كان يحمل خمسةً وعشرين استيرادًا
 * وسجلَّي شاشات، فصارت السجلّات في `screens/registry.ts`
 * و`screens/admin/registry.ts` وبقي هنا سؤالُ «أيّ قشرة لأيّ شاشة» وحده.
 */
import { useEffect } from 'react'

import { go, init, listen } from './nav/history'
import { isAdminScreen } from './nav/adminNav'
import { useScreen } from './nav/useNavigation'
import AdminShell from './screens/admin/AdminShell'
import Login from './screens/Login'
import PilotShell from './screens/PilotShell'
import { PILOT_SUB, PILOT_TABS } from './screens/registry'
import { AppStateProvider, useApp } from './state/AppState'

function Shell({ children }: { children: React.ReactNode }) {
  return <div className="mx-auto w-full max-w-[520px] px-5 pt-8 pb-12">{children}</div>
}

function Booting() {
  return (
    <Shell>
      <p className="text-[14px] text-(--color-text-dim)">جارٍ التحقّق…</p>
    </Shell>
  )
}

function SessionError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <Shell>
      <p role="alert" className="mb-4 text-[14px] text-(--color-red-text)">
        {message}
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="min-h-[44px] rounded-(--radius-sm) border border-(--color-border-strong) px-5 text-[14px]"
      >
        إعادة المحاولة
      </button>
    </Shell>
  )
}

function NotForYou() {
  return (
    <Shell>
      <p className="mb-4 text-[14px] text-(--color-text-dim)">
        هذه الشاشة للمشرفين. بطاقتك من هنا.
      </p>
      <button
        type="button"
        onClick={() => go('deck')}
        className="min-h-[44px] rounded-(--radius-sm) border border-(--color-border-strong) px-5 text-[14px]"
      >
        بطاقتي
      </button>
    </Shell>
  )
}

function Gate() {
  const { status, error, refresh, user } = useApp()
  const screen = useScreen()

  useEffect(() => {
    init()
    return listen()
  }, [])

  if (status === 'checking') return <Booting />
  if (status === 'error') {
    return <SessionError message={error?.message ?? 'تعذّر التحقّق من الجلسة.'} onRetry={refresh} />
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

  const SubScreen = PILOT_SUB[screen]
  if (SubScreen) {
    return (
      <Shell>
        <SubScreen />
      </Shell>
    )
  }

  // **حرسُ الدور هنا إنصافٌ لا أمن** — `@admin_required` في الخادم هو الحاكم
  // (`AGENTS.md` ٩). وجودُه يمنع طالبًا يفتح رابطًا عميقًا من مواجهة قشرةٍ
  // كل نداءٍ فيها ٤٠٣.
  if (isAdminScreen(screen)) {
    if (user?.role !== 'admin') return <NotForYou />
    return <AdminShell screen={screen} />
  }

  return (
    <Shell>
      <p className="text-[14px] text-(--color-text-dim)">الشاشة: {screen}</p>
    </Shell>
  )
}

export default function App() {
  return (
    <AppStateProvider>
      <Gate />
    </AppStateProvider>
  )
}
