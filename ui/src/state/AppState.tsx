/**
 * هوية الجلسة وحدها — **لا بيانات نطاق**.
 *
 * بطاقة الطيّار وقوائمه يملكها من يعرضها عبر `useAsync`، فلا يصير هذا الملفّ
 * مخزنًا عامًّا يُحدَّث من كل مكان ويُقرأ من كل مكان.
 *
 * **والحالة ثلاثية لا ثنائية:** `'checking'` موجودة لأن ثنائيةً (`in`/`out`)
 * تُظهر شاشة الدخول للحظة لمستخدمٍ **مسجَّل أصلًا** قبل أن يردّ `/auth/me` —
 * وميضٌ يُقلق ويبدو عطلًا.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

import { api, ApiError } from '../api'
import type { Identity } from '../api/types/auth'

type Status = 'checking' | 'in' | 'out' | 'error'
type Session = { status: Status; user: Identity | null; error: ApiError | null }

type Ctx = Session & {
  refresh: () => void
  login: (studentNo: string, pin: string) => Promise<void>
  logout: () => Promise<void>
}

const AppCtx = createContext<Ctx | null>(null)

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session>({
    status: 'checking',
    user: null,
    error: null,
  })

  const refresh = useCallback(() => {
    setSession({ status: 'checking', user: null, error: null })
    api.auth
      .me()
      .then(({ user }) => setSession({ status: 'in', user, error: null }))
      .catch((error: unknown) => {
        // **٤٠١ حالةٌ طبيعية لا عطل:** زائرٌ لم يدخل بعد. وأي رمزٍ آخر عطلٌ
        // يُعرَض للمستخدم — والخلط بينهما يجعل الشبكة المقطوعة تبدو «تسجيل خروج».
        const out = error instanceof ApiError && error.status === 401
        setSession({
          status: out ? 'out' : 'error',
          user: null,
          error: out ? null : (error as ApiError),
        })
      })
  }, [])

  useEffect(refresh, [refresh])

  const login = useCallback(async (studentNo: string, pin: string) => {
    const { user } = await api.auth.login(studentNo, pin)
    setSession({ status: 'in', user, error: null })
  }, [])

  const logout = useCallback(async () => {
    try {
      await api.auth.logout()
    } finally {
      // `finally` مقصود: خروجٌ محلّيّ ينجح دائمًا، فلا يحبس المستخدمَ فشلُ طلب.
      setSession({ status: 'out', user: null, error: null })
    }
  }, [])

  const value = useMemo<Ctx>(
    () => ({ ...session, refresh, login, logout }),
    [session, refresh, login, logout]
  )
  return <AppCtx.Provider value={value}>{children}</AppCtx.Provider>
}

export function useApp(): Ctx {
  const ctx = useContext(AppCtx)
  if (!ctx) throw new Error('useApp خارج AppStateProvider')
  return ctx
}
