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

export type OrgTahdirRow = {
  user_id: Count
  full_name: string
  days_completed: Count
  pages_total: Count
  percent: Pct
  struggling: boolean
}

export type OrgTahdirReport = { week_start: string; students: OrgTahdirRow[] }
