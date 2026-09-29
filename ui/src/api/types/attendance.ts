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

// ═══ الحضور من راصد — للعرض فقط (و-٢٠) ═══

/** الحضور **عددٌ** من أيام التسميع لا حاضر/غائب — هكذا يصل من راصد فعلًا. */
export type RasdAttendanceRow = {
  name: string
  team_name: string | null
  attendance: string
  tasmi3_days: string
  matched: boolean
}

/** `imported_at: null` قبل أوّل استيراد — حالةٌ مصمَّمة لا عطل. */
export type RasdLatestImport = { imported_at: string | null; rows: RasdAttendanceRow[] }
