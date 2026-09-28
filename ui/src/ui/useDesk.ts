import { useSyncExternalStore } from 'react'

/**
 * هل نحن فوق حدّ ١٠٢٤px؟ — **المصدر الوحيد لهذا السؤال في الواجهة.**
 *
 * مخزنٌ وحيد + `useSyncExternalStore`، نفس شكل `nav/history.ts`
 * و`ui/toastStore.ts`: استعلامٌ واحد مهما كثر المستهلكون، وقراءةٌ متّسقة مع
 * الرسم بلا `useEffect` يتأخّر إطارًا.
 *
 * **والحدّ يُقرأ من الرمز لا يُكتب هنا:** `--breakpoint-desk` يصل إلى
 * `:root` فعلًا (يُصدره Tailwind من `@theme`)، فيُقرأ منه — وإلّا صار الرقم
 * مكتوبًا في موضعين يتباعدان. و`FALLBACK` لأجل jsdom وحده: لا يعالج CSS
 * فيعيد `getComputedStyle` نصًّا فارغًا. **ويربطه بالرمز فحصُ
 * `check-responsive.mjs`** فلا ينزلق أحدهما عن الآخر بصمت.
 */
const FALLBACK = '1024px'

let media: MediaQueryList | null = null

function query(): MediaQueryList {
  if (media) return media
  const token = getComputedStyle(document.documentElement)
    .getPropertyValue('--breakpoint-desk')
    .trim()
  media = window.matchMedia(`(width >= ${token || FALLBACK})`)
  return media
}

function subscribe(onChange: () => void): () => void {
  const m = query()
  m.addEventListener('change', onChange)
  return () => m.removeEventListener('change', onChange)
}

const getSnapshot = (): boolean => query().matches

// أوّليّةُ الجوّال هي الافتراض قبل أن يُعرف المقاس — لا العكس.
const getServerSnapshot = (): boolean => false

export function useDesk(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
}
