/** قائمة أسماء وحدها — `GET /admin/quran/students` (`schemas/quran.py`).
 * سحبٌ مبكّر صغير من نطاق و-١٨ لأجل نموذج الإدخال المباشر في طابور تحضير
 * القراءة (`و-١٧.md` §٢ قرار ٧) — بلا أي حقل مجال. */
import type { Count } from '../brand'

export type StudentRef = { id: Count; full_name: string }
export type QuranRoster = { students: StudentRef[] }
