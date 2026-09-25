import { useEffect, useState } from 'react'

/**
 * `false` عند الرسم الأوّل ثم `true` بعد التركيب — لإطلاق انتقال CSS من
 * حالة الصفر لا القفز إليها مباشرةً. تُستعمل في البدائيات ذات القيمة
 * الواحدة المتحرّكة (`ProgressBar`, `FuelDial`, `ChartBars`) التي يكفيها
 * انتقال CSS عاديّ — احترام `prefers-reduced-motion` هنا **مجّانيّ**
 * بالقاعدة الشاملة في `base.css` (تُصفّر مدّة كل انتقال CSS)، فلا حاجة
 * لفحصه هنا ثانيةً؛ خلاف توينات GSAP في `mo.ts` التي لا تحترم تلك القاعدة.
 */
export function useEnter(): boolean {
  const [entered, setEntered] = useState(false)
  useEffect(() => {
    const id = requestAnimationFrame(() => setEntered(true))
    return () => cancelAnimationFrame(id)
  }, [])
  return entered
}
