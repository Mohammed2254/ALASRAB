import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import { ApiError, api } from '../lib/api'

/*
  حالة الجلسة وحدها — **هويةٌ لا بيانات**.

  البطاقة لا تُحفظ هنا: مالكها `PilotDeck` عبر `useAsync`، فتُجلب حين تُعرض
  وتُحدَّث بإعادة تحميلها. وضعُها في حالة عامّة يجعل كل شاشة لاحقة تتساءل
  أهي طازجة، ويخلق مخزنًا يكبر بلا حدّ.

  ولا Redux ولا مخزن عامّ: شاشتان وحالة واحدة — `Context` يكفي، وما زاد
  بنيةٌ تحتية لشاشات لم تُبنَ بعد.
*/

const Ctx = createContext(null)

export function AppStateProvider({ children }) {
  // 'checking' حالة ثالثة ضرورية: بدونها تومض شاشة الدخول لمن هو داخل أصلًا،
  // لأن أوّل رسمة تسبق جواب الخادم.
  const [session, setSession] = useState({ status: 'checking', user: null, error: null })

  const load = useCallback(async () => {
    try {
      const data = await api.me()
      setSession({ status: 'in', user: data.user, error: null })
    } catch (error) {
      // ٤٠١ ليست عطلًا بل الحالة الطبيعية لزائر لم يدخل بعد.
      const out = error instanceof ApiError && error.status === 401
      setSession({
        status: out ? 'out' : 'error',
        user: null,
        error: out ? null : error,
      })
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const login = useCallback(
    async (studentNo, pin) => {
      await api.login(studentNo, pin)
      await load()
    },
    [load],
  )

  const logout = useCallback(async () => {
    // الخروج ينجح حتى بجلسة منتهية (٢٠٤)؛ ولو تعطّل الطلب فالمستخدم يخرج
    // محليًّا على أي حال — إبقاؤه محتجزًا في شاشة لا يخرج منها أسوأ من الخطأ.
    try {
      await api.logout()
    } finally {
      setSession({ status: 'out', user: null, error: null })
    }
  }, [])

  const value = useMemo(
    () => ({ ...session, refresh: load, login, logout }),
    [session, load, login, logout],
  )

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useApp() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useApp must be used inside AppStateProvider')
  return ctx
}
