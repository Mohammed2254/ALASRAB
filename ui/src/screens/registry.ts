/**
 * سجلّا شاشات الطيّار — مفصولان عن `App.tsx` فيبقى ذاك تحكّمًا لا جدولًا.
 *
 * **والشاشات الإدارية ليست هنا** (و-٢٠): كانت الخمس عشرة محشوّةً في
 * `SUB_SCREENS` نفسه، فصار سجلٌّ واحد يخدم قشرتين مختلفتين — وهو ما جعل
 * لوحة المشرف تُرسَم في عمود ٥٢٠px عارٍ بلا هيكل. صار لها
 * `admin/registry.ts` وقشرتها.
 */
import type { ScreenKey } from '../nav/routes'

import Boards from './Boards'
import DailyQuestion from './DailyQuestion'
import Deck from './Deck'
import Formation from './Formation'
import Readings from './Readings'
import Station from './Station'
import SubmitNote from './SubmitNote'
import Tahdir from './Tahdir'
import WeekPilot from './WeekPilot'

/** الخمس على شريط التبويب (و-١٥) — إضافة شاشة سطرٌ واحد. */
export const PILOT_TABS: Partial<Record<ScreenKey, () => React.JSX.Element>> = {
  deck: Deck,
  readings: Readings,
  station: Station,
  formation: Formation,
  board: Boards,
}

/** الفرعية الأربع — تُرسَم في `Shell` بسيط بـ`Subback` خاصّتها لا شريط تبويب. */
export const PILOT_SUB: Partial<Record<ScreenKey, () => React.JSX.Element>> = {
  tahdir: Tahdir,
  question: DailyQuestion,
  weekPilot: WeekPilot,
  note: SubmitNote,
}
