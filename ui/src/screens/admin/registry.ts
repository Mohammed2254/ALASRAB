/**
 * مفتاح الشاشة الإدارية ⇒ مكوّنها. **الملفّ الوحيد الذي يستورد شاشات المشرف.**
 *
 * حصرُ الاستيراد في ملفٍّ واحد هو ما يجعل تقسيم الحزمة ممكنًا لاحقًا: القشرة
 * تستورد هذا السجلّ، والسجلّ يسحب الشاشات — فحدُّ التقسيم سطرٌ واحد في القشرة
 * لا خمسة عشر استيرادًا موزّعًا على `App.tsx`.
 *
 * و`Record<AdminKey, …>` **مُستوفًى بالمترجم**: مسارٌ يُضاف إلى `ADMIN_PATHS`
 * بلا شاشة هنا يُسقط `tsc` فورًا — لا شاشةَ مفقودة تُكتشَف بالنقر.
 */
import type { AdminKey } from '../../nav/adminNav'

import Attendance from './Attendance'
import DailyQuestions from './DailyQuestions'
import Dashboard from './Dashboard'
import AuditLog from './AuditLog'
import FuelActivities from './FuelActivities'
import FuelAssess from './FuelAssess'
import Notes from './Notes'
import QuranEdit from './QuranEdit'
import RasdImport from './RasdImport'
import ReadingQueue from './ReadingQueue'
import Report from './Report'
import Students from './Students'
import TahdirQueue from './TahdirQueue'
import TahdirReport from './TahdirReport'
import Teams from './Teams'
import Thresholds from './Thresholds'
import Weights from './Weights'
import WeekPilot from './WeekPilot'

export const ADMIN_SCREENS: Record<AdminKey, () => React.JSX.Element> = {
  adminDashboard: Dashboard,
  adminQueue: ReadingQueue,
  adminTahdirQueue: TahdirQueue,
  adminNotes: Notes,
  adminReport: Report,
  adminTahdirReport: TahdirReport,
  adminAudit: AuditLog,
  adminStudents: Students,
  adminTeams: Teams,
  adminWeights: Weights,
  adminThresholds: Thresholds,
  adminWeekPilot: WeekPilot,
  adminAttendance: Attendance,
  adminQuestions: DailyQuestions,
  adminFuelActivities: FuelActivities,
  adminFuelAssess: FuelAssess,
  adminQuranEdit: QuranEdit,
  adminRasdImport: RasdImport,
}
