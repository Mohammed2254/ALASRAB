/**
 * التنقّل فوق History API — ADR-008. بلا موجّه مسارات وبلا اعتمادية.
 *
 * **لماذا هذا الملفّ موجود أصلًا؟** لأن سجلّ الشاشات في البناء الأول لا يُنشئ
 * مدخلات في سجلّ المتصفّح، فأوّل ضغطة على زرّ رجوع أندرويد **تخرج من الموقع**.
 * وطلابنا الثلاثون على جوّالات، وضغطة الرجوع عندهم حركةٌ لا قرار.
 *
 * والمتجر مبنيٌّ لـ`useSyncExternalStore`: مصدرُ الحقيقة هو المتصفّح نفسه
 * (`location` و`history`) لا نسخةٌ في React تتباعد عنه عند الرجوع.
 */

import { keyOf, pathOf, ROOT_KEY, type ScreenKey } from './routes'

type Listener = () => void

const listeners = new Set<Listener>()
let current: ScreenKey = ROOT_KEY

const emit = () => listeners.forEach((fn) => fn())

/**
 * تهيئةٌ تُستدعى مرّة بعد حسم الهوية.
 *
 * `replaceState` لا `pushState`: الشاشة الأولى **تحلّ محلّ** المدخل الابتدائي
 * ولا تُضاف فوقه، وإلّا احتاج الطالب ضغطتَي رجوع للخروج من أوّل شاشة —
 * وهو الفخّ الذي تصنعه معظم التطبيقات بلا قصد.
 */
export function init(): void {
  current = keyOf(window.location.pathname)
  window.history.replaceState({ key: current }, '', pathOf(current))
  // استعادةُ موضع التمرير تلقائيًّا تقفز بالشاشة الجديدة إلى منتصفها.
  if ('scrollRestoration' in window.history) window.history.scrollRestoration = 'manual'
}

/** الشاشة الحالية — يقرؤها `useSyncExternalStore`. */
export const getScreen = (): ScreenKey => current

export function subscribe(listener: Listener): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

/**
 * انتقالٌ يُضيف مدخلًا — فالرجوع يعود إلى ما قبله.
 *
 * **وإعادة الانتقال إلى الشاشة نفسها لا تفعل شيئًا:** نقرُ التبويب النشط
 * مرّتين لا يجوز أن يُنتج مدخلين، وإلّا احتاج الطالب ضغطتَي رجوع ليغادر
 * شاشةً دخلها مرّة (ق-٢٢١).
 */
export function go(key: ScreenKey): void {
  if (key === current) return
  current = key
  window.history.pushState({ key }, '', pathOf(key))
  window.scrollTo(0, 0)
  emit()
}

/** استبدالٌ بلا مدخل جديد — للدخول والخروج، حيث لا معنى للرجوع. */
export function replace(key: ScreenKey): void {
  current = key
  window.history.replaceState({ key }, '', pathOf(key))
  emit()
}

/**
 * يُستدعى مرّة عند التركيب.
 *
 * والحالة تُقرأ من `event.state` إن وُجدت ومن المسار إن غابت — لأن المدخل
 * الذي أنشأه المتصفّح قبل التهيئة (أو أعاد إنشاءه بعد تحديث) بلا `state`.
 */
export function listen(): () => void {
  const onPop = (event: PopStateEvent) => {
    const state = event.state as { key?: ScreenKey } | null
    current = state?.key ?? keyOf(window.location.pathname)
    emit()
  }
  window.addEventListener('popstate', onPop)
  return () => window.removeEventListener('popstate', onPop)
}
