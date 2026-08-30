import { useCallback, useEffect, useState } from 'react'

/*
  جلب بيانات بحالاته الثلاث صريحةً: تحميل، خطأ، بيانات.

  لا حالة رابعة صامتة: كل شاشة تعرض واحدة من الثلاث، فلا تبقى صفحة فارغة بلا
  تفسير — وهي أسوأ ما يواجه مستخدمًا لأنه لا يعرف أينتظر أم يعيد المحاولة.
*/
export function useAsync(fn, deps = []) {
  const [state, setState] = useState({ status: 'loading', data: null, error: null })

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(fn, deps)

  const reload = useCallback(() => {
    let alive = true
    setState({ status: 'loading', data: null, error: null })
    run()
      .then((data) => alive && setState({ status: 'ready', data, error: null }))
      .catch((error) => alive && setState({ status: 'error', data: null, error }))
    return () => {
      alive = false
    }
  }, [run])

  useEffect(reload, [reload])

  return { ...state, reload }
}
