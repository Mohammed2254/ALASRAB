/**
 * عقد بطاقة الطيّار — `GET /me/deck` · `GET /me/events`.
 *
 * **لاحظ الخلط المتعمَّد في `nextRank`:** `atHours` و`remaining` عشريّان نصّيّان
 * و`progressPct` رقمٌ حقيقيّ — في الكائن نفسه. وهذا هو بالضبط ما يجعل الوسم
 * ضروريًّا لا زينةً (ADR-009).
 */
import type { Count, Decimal, Pct } from '../brand'

export type Rank = { name: string; tier: Count }

export type NextRank = {
  name: string
  at_hours: Decimal
  progress_pct: Pct
  remaining: Decimal
}

export type Flight = { grounded: boolean; last_activity_on: string | null }

export type TeamRef = { name: string; rank_in_org: Count | null }

export type Deck = {
  rank: Rank
  hours: Decimal
  next_rank: NextRank | null
  flight: Flight
  team: TeamRef | null
}

export type LedgerEvent = {
  id: Count
  kind: string
  delta: Decimal
  occurred_on: string
  reason: string | null
}
