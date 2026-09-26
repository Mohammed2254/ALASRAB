/** التقرير الدوري — `schemas/report.py`. `ResetPin` (`schemas/audit.py`)
 * يعيش هنا لا في ملفّ مستقلّ — مكانه الوحيد استهلاكًا هو صفّ الطائرة
 * الأرضية في هذا التقرير (`و-١٧.md` §٢ قرار ٤). */
import type { Count, Decimal } from '../brand'

export type ReportWindow = { from: string; to: string; days: Count }
export type ReportTotals = { hours: Decimal; active_pilots: Count; grounded_pilots: Count }
export type ReportTeamRow = { id: Count; name: string; hours: Decimal; members: Count; avg_hours: Decimal }
export type Mover = { user_id: Count; full_name: string; hours: Decimal }
export type Grounded = { user_id: Count; full_name: string; last_activity_on: string | null }

export type Report = {
  window: ReportWindow
  totals: ReportTotals
  teams: ReportTeamRow[]
  top_movers: Mover[]
  grounded: Grounded[]
}

export type ResetPinResult = { student_no: string; pin: string }
