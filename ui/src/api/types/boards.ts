/**
 * عقد اللوحات — `GET /boards/{pilots,teams,formation}` (`schemas/standings.py`).
 *
 * **نافذتان مختلفتان عمدًا:** الأفراد والأسراب بنافذة الأسبوع الحالي
 * (`orgs.week_starts_on`)، والتشكيل تراكميّ — نصّ ط-٨ لا يذكر نافذة خلافًا
 * لِط-٧ (`API.md`). ليس سهوًا، فلا يُوحَّدان هنا.
 */
import type { Count, Decimal } from '../brand'

export type PilotRow = { full_name: string; hours: Decimal }

export type Readiness = { flying: Count; grounded: Count }

export type TeamBoardRow = {
  team: string
  code: string
  avg_hours: Decimal
  members: Count
  readiness: Readiness
}

export type Aircraft = {
  name: string | null
  size: Decimal
  size_pct: Count
  grounded: boolean
}

export type FormationScope = 'team' | 'general'

export type Formation = { scope: FormationScope; aircraft: Aircraft[] }
