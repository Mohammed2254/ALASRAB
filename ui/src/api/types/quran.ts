/**
 * التصحيح والتعديل القرآني — `schemas/quran.py` (FR-035..037 · FR-080).
 * `StudentRef`/`QuranRoster` كانتا في `types/quranRoster.ts` — سحبٌ مبكّر
 * من و-١٧ لأجل طابور تحضير القراءة (`و-١٧.md §٢` قرار ٧). أُعيدت التسمية
 * هنا واتّسعت لتشمل بقية `quran.py` بدل ملفّين لمصدر خلفيّ واحد (`و-١٨.md
 * §٢` قرار ١).
 */
import type { Count, Decimal } from '../brand'

export type StudentRef = { id: Count; full_name: string }
export type QuranRoster = { students: StudentRef[] }

export type QuranEventRow = { id: Count; kind: string; delta: Decimal; occurred_on: string; reason: string | null }
export type QuranEventsList = { events: QuranEventRow[] }

export type ReversedEvent = { id: Count; delta: Decimal; kind: string }

/** `quantity` نصٌّ من حقل إدخال — التحويل في `endpoints/admin.ts` (حدّ الشبكة). */
export type AddQuranEntryForm = {
  user_id: string
  occurred_on: string
  activity_type: string
  quantity: string
  mastery: string | null
  reason: string
}
export type AddedQuranEntry = { id: Count; delta: Decimal; kind: string }
