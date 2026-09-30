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
import { lazy, Suspense, useEffect } from 'react'

import { go, init, listen } from './nav/history'
import { isAdminScreen } from './nav/adminNav'
import { useScreen } from './nav/useNavigation'
/**
 * **حدّ التقسيم: سطحُ المشرف كلّه جزءًا واحدًا.**
 *
 * الطالب لا يحتاج كود المشرف إطلاقًا، وكان ينزّله كاملًا. و«جزءٌ لكل شاشة»
 * كان سيعني ستّ عشرة رحلة شبكة متسلسلة على جوّال المشرف المتطوّع — وهو
 * بعينه الاحتكاك الذي يغذّي تأجيل الإدخال (الخطر خ-١). فجزءٌ واحد، يُسخَّن
 * على النيّة.
 */
const AdminShell = lazy(() => import('./screens/admin/AdminShell'))
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

/**
 * بديلُ التعليق — **مؤثَّثٌ في الحزمة الأساسية** بنفس هندسة القشرة، فلا
 * نقزةَ تخطيط حين يصل الجزء. ولأن `AdminShell` لا يُفكَّك بعد وصوله، يُرى
 * هذا مرّةً واحدة في الجلسة لا عند كل تنقّلٍ إداريّ.
 */
function AdminFallback() {
  return (
    <div className="desk:grid desk:grid-cols-[250px_minmax(0,1fr)]">
      <div className="hidden border-s border-(--color-border) bg-(--color-bg-2) desk:block desk:h-dvh" />
      <div className="min-w-0 px-4 pt-8 desk:px-6">
        <p className="text-[14px] text-(--color-text-dim)">جارٍ فتح لوحة المشرف…</p>
      </div>
    </div>
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
    return (
      <Suspense fallback={<AdminFallback />}>
        <AdminShell screen={screen} />
      </Suspense>
    )
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
