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
import Login from './screens/Login'
import { AppStateProvider, useApp } from './state/AppState'

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
