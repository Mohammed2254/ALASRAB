/** الحضور الاحتياطي — `schemas/entry.py` (FR-041 · FR-042). */
import type { Count, Decimal } from '../brand'

export type PilotRosterRow = { user_id: Count; full_name: string }

export type AttendanceStatus = {
  week_start: string
  already_recorded: boolean
  pilots: PilotRosterRow[]
  absent_user_ids: Count[]
  undo_until: string | null
}

export type RecordedAttendance = { present: Count; absent: Count; hours_each: Decimal; undo_until: string }
export type UndoneAttendance = { reversed: Count }
