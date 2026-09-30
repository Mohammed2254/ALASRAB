/**
 * طابورا القراءة وتحضير القراءة — الشقّ الإداريّ من `schemas/reading.py`.
 * الشقّ الطيّاريّ (نفس الملفّ الخلفيّ) في `types/me.ts` — مقسَّمان بحسب من
 * يراهما لا حسب الملفّ الخلفيّ الواحد (`و-١٧.md` §٢ قرار ٢).
 */
import type { Count, Decimal, Pct } from '../brand'

export type QueueItem = {
  id: Count
  student_name: string
  read_on: string
  pages: Count
  book_title: string
  created_at: string
}

export type ReviewResult = { submission_id: Count; status: string; hours: Decimal | null }

export type AdminTahdirEntryForm = {
  user_id: string
  read_on: string
  pages: string
  book_title: string
}

export type AdminEntryResult = { id: Count; status: string; hours: Decimal | null }

/** درجةُ انتظام **محسوبة في الخادم** بعتبتَي النموذج — الواجهة تُلوّن وتُسمّي. */
export type TahdirTier = 'good' | 'fair' | 'low'

export type OrgTahdirRow = {
  user_id: Count
  full_name: string
  team_name: string
  days_completed: Count
  days_total: Count
  pages_total: Count
  percent: Pct
  tier: TahdirTier
  struggling: boolean
}

export type OrgTahdirTotals = { pages: Count; participants: Count; fully_regular: Count }

export type OrgTahdirReport = {
  from_day: string
  to_day: string
  days_total: Count
  totals: OrgTahdirTotals
  students: OrgTahdirRow[]
}
