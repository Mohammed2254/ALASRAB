/**
 * ربط متجر التنقّل بـReact — `useSyncExternalStore`.
 *
 * وهو الخطّاف الصحيح هنا لا `useState`: مصدر الحقيقة خارج React (المتصفّح)،
 * وضغطةُ الرجوع تغيّره بلا علم React. و`useState` كان سيحتفظ بنسخةٍ تتباعد
 * عن `location` عند أوّل رجوع.
 */
import { useSyncExternalStore } from 'react'

import { getScreen, subscribe } from './history'
import type { ScreenKey } from './routes'

export function useScreen(): ScreenKey {
  return useSyncExternalStore(subscribe, getScreen, getScreen)
}
