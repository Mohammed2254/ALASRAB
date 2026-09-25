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

/** `GET /me/readings` — صفّ واحد. `hours` تصل فقط بعد اعتماد المشرف. */
export type MyReading = {
  id: Count
  read_on: string
  pages: Count
  book_title: string
  status: 'pending' | 'approved' | 'rejected'
  review_reason: string | null
  hours: Decimal | null
}

/** `POST /me/readings` — جسم الطلب السلكيّ (بعد التحويل عن نموذج). */
export type SubmitReading = { read_on: string; pages: number; book_title: string }

/**
 * نموذج الإرسال كما يكتبه الطالب — `pages` نصٌّ من حقل إدخال. التحويل إلى
 * `number` يقع في `endpoints/me.ts` (حدّ الشبكة)، لا في الشاشة: `Number()`
 * ممنوعةٌ فيها بفحص AST (ADR-009 نفس منطقه، لا حسابٌ في طبقة العرض).
 */
export type SubmitReadingForm = { read_on: string; pages: string; book_title: string }

/** `GET /station` — محطة التزوّد. `team: null` لطيّار بلا عضوية سارية. */
export type StationTeam = { name: string; litres: Decimal }

export type RecentAssessment = {
  activity_name: string
  occurred_on: string
  total_pct: Decimal
  litres: Decimal
}

export type Station = {
  team: StationTeam | null
  tank_capacity_l: Decimal | null
  recent: RecentAssessment[]
}
