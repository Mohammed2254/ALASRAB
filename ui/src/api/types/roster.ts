/**
 * سجلّ الطلاب — `schemas/roster.py` (و-٢١).
 *
 * **لا بند `SCOPE.md` لإنشاء طالب**: فيه `FR-004` (إعادة تعيين رمز) و`FR-083`
 * (إدارة الأسراب)، وفُرض أن الطلاب موجودون سلفًا. هذه الأنواع تخدم المسار
 * الذي أُضيف ليُجيب «من أين؟».
 */
import type { Count } from '../brand'

export type RosterRow = {
  id: Count
  full_name: string
  student_no: string
  role: string
  /** العدم = عضويةٌ أُغلقت (نقلٌ قديم) — يظهر بلا سرب لا يختفي من السجلّ. */
  team_name: string | null
  is_active: boolean
}

export type RosterList = { students: RosterRow[] }

/**
 * `pin` نصًّا — **الموضع الوحيد في العقد الذي يحمل رمزًا صريحًا**، ولمرّةٍ
 * واحدة لحظة الإنشاء. ولا يظهر في أيّ قراءة: `RosterRow` بلا حقل رمز بالبناء.
 */
export type IssuedStudent = {
  id: Count
  full_name: string
  student_no: string
  pin: string
}

export type CreateStudentForm = { full_name: string; student_no: string; team_id: string }
export type BulkStudentRow = { full_name: string; student_no: string }
export type BulkFailure = { line: Count; message: string }
export type BulkCreated = { created: IssuedStudent[]; failed: BulkFailure[] }

export type RoleSet = { id: Count; role: string }
export type ActiveSet = { id: Count; is_active: boolean }
