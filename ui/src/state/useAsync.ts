/**
 * جلبٌ بثلاث حالات صريحة — **ولا رابعة صامتة**.
 *
 * `loading` · `ready` · `error`، ولكلٍّ عرضٌ مصمَّم (`SCOPE.md §١٠.٣`). والحالة
 * الرابعة الصامتة (بيانات فارغة تُعرض كأنها جاهزة) هي ما يجعل شاشةً بيضاء
 * تبدو «تعمل».
 */
import { useCallback, useEffect, useState } from 'react'

type State<T> =
  | { status: 'loading'; data: null; error: null }
  | { status: 'ready'; data: T; error: null }
  | { status: 'error'; data: null; error: Error }

export type Async<T> = State<T> & { reload: () => void }

export function useAsync<T>(fn: () => Promise<T>, deps: unknown[] = []): Async<T> {
  const [state, setState] = useState<State<T>>({ status: 'loading', data: null, error: null })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(fn, deps)

  const reload = useCallback(() => {
    let alive = true
    setState({ status: 'loading', data: null, error: null })
    run()
      .then((data) => alive && setState({ status: 'ready', data, error: null }))
      .catch((error: Error) => alive && setState({ status: 'error', data: null, error }))
    // حارس التفكيك: ردٌّ يصل بعد إزالة المكوّن لا يُحدّث حالةً ميّتة.
    return () => {
      alive = false
    }
  }, [run])

  useEffect(reload, [reload])
  return { ...state, reload }
}
